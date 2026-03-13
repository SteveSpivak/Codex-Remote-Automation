import Foundation

@MainActor
final class RelayClient: ObservableObject {
    @Published var status: String = "disconnected"
    @Published var snapshot: PendingApprovalsSnapshot?

    private var socketTask: URLSessionWebSocketTask?
    private let session = URLSession(configuration: .default)
    private var secureState: SecureSessionState?
    private var pairingPayload: PairingPayload?

    func connect(pairingPayload: PairingPayload, phoneDeviceId: String, phoneLabel: String) async throws {
        self.pairingPayload = pairingPayload
        guard let url = URL(string: "\(pairingPayload.relayUrl)/session/\(pairingPayload.sessionId)?role=iphone") else {
            throw URLError(.badURL)
        }
        let clientNonce = SecureChannel.randomBase64()
        let hello = ClientHello(
            protocolVersion: pairingPayload.protocolVersion,
            sessionId: pairingPayload.sessionId,
            handshakeMode: "qr_bootstrap",
            phoneDeviceId: phoneDeviceId,
            phoneLabel: phoneLabel,
            clientNonce: clientNonce,
            clientProof: try SecureChannel.computeTag(
                secret: pairingPayload.pairingSecret,
                aad: SecureChannel.handshakeAAD(
                    sessionId: pairingPayload.sessionId,
                    handshakeMode: "qr_bootstrap",
                    phoneDeviceId: phoneDeviceId,
                    clientNonce: clientNonce
                ),
                ciphertext: Data()
            )
        )

        let task = session.webSocketTask(with: url)
        task.resume()
        self.socketTask = task
        self.status = "connecting"
        try await send(hello)
        try await listenForMessages(phoneDeviceId: phoneDeviceId, pairingSecret: pairingPayload.pairingSecret, clientNonce: clientNonce)
    }

    func requestPendingApprovals() async throws {
        try await send([
            "id": UUID().uuidString,
            "method": "bridge/getPendingApprovals"
        ])
    }

    func respondApproval(_ request: ApprovalDecisionRequest) async throws {
        try await send([
            "id": UUID().uuidString,
            "method": "bridge/respondApproval",
            "params": [
                "requestId": request.requestId,
                "decision": request.decision,
                "operatorNote": request.operatorNote as Any
            ]
        ])
    }

    private func listenForMessages(phoneDeviceId: String, pairingSecret: String, clientNonce: String) async throws {
        while let task = socketTask {
            let message = try await task.receive()
            guard case let .string(text) = message else { continue }
            try await handleIncoming(text: text, phoneDeviceId: phoneDeviceId, pairingSecret: pairingSecret, clientNonce: clientNonce)
        }
    }

    private func handleIncoming(text: String, phoneDeviceId: String, pairingSecret: String, clientNonce: String) async throws {
        guard let data = text.data(using: .utf8) else { return }
        let object = try JSONSerialization.jsonObject(with: data)
        guard let payload = object as? [String: Any], let kind = payload["kind"] as? String else {
            try handleBridgePayload(data)
            return
        }

        if kind == "serverHello" {
            let serverData = try JSONSerialization.data(withJSONObject: payload)
            let serverHello = try JSONDecoder().decode(ServerHello.self, from: serverData)
            let auth = ClientAuth(
                sessionId: serverHello.sessionId,
                phoneDeviceId: phoneDeviceId,
                keyEpoch: serverHello.keyEpoch,
                clientAuth: try SecureChannel.computeTag(
                    secret: pairingSecret,
                    aad: SecureChannel.authAAD(
                        sessionId: serverHello.sessionId,
                        phoneDeviceId: phoneDeviceId,
                        clientNonce: clientNonce,
                        serverNonce: serverHello.serverNonce,
                        keyEpoch: serverHello.keyEpoch
                    ),
                    ciphertext: Data("clientAuth".utf8)
                )
            )
            let sessionSecret = try SecureChannel.deriveBytes(
                secret: pairingSecret,
                parts: ["session", serverHello.sessionId, phoneDeviceId, clientNonce, serverHello.serverNonce, String(serverHello.keyEpoch)]
            ).base64EncodedString()
            secureState = SecureSessionState(
                sessionId: serverHello.sessionId,
                phoneDeviceId: phoneDeviceId,
                sessionSecret: Data(base64Encoded: sessionSecret) ?? Data(),
                keyEpoch: serverHello.keyEpoch,
                nextOutboundCounter: 1,
                lastInboundCounter: 0,
                lastAppliedBridgeOutboundSeq: 0
            )
            try await send(auth)
            status = "pairing"
            return
        }

        if kind == "secureReady" {
            guard let state = secureState else { return }
            let resume = ResumeState(sessionId: state.sessionId, keyEpoch: state.keyEpoch, lastAppliedBridgeOutboundSeq: state.lastAppliedBridgeOutboundSeq)
            try await send(resume)
            status = "connected"
            try await send([
                "id": UUID().uuidString,
                "method": "initialize",
                "params": ["client": "cra-ios", "version": "0.1.0"]
            ])
            try await requestPendingApprovals()
            return
        }

        if kind == "encryptedEnvelope", let secureState {
            let envelopeData = try JSONSerialization.data(withJSONObject: payload)
            let envelope = try JSONDecoder().decode(EncryptedEnvelope.self, from: envelopeData)
            let secret = secureState.sessionSecret.base64EncodedString()
            let plaintext = try SecureChannel.decrypt(
                secret: secret,
                aad: SecureChannel.envelopeAAD(sessionId: envelope.sessionId, keyEpoch: envelope.keyEpoch, sender: envelope.sender, counter: envelope.counter),
                ciphertext: envelope.ciphertext,
                tag: envelope.tag
            )
            try handleBridgePayload(Data(plaintext.utf8))
        }
    }

    private func handleBridgePayload(_ data: Data) throws {
        let object = try JSONSerialization.jsonObject(with: data)
        guard let payload = object as? [String: Any] else { return }
        if let result = payload["result"] as? [String: Any],
           let snapshotData = try? JSONSerialization.data(withJSONObject: result),
           let snapshot = try? JSONDecoder().decode(PendingApprovalsSnapshot.self, from: snapshotData) {
            self.snapshot = snapshot
            return
        }
        if payload["method"] as? String == "bridge/pendingApprovalsUpdated",
           let params = payload["params"] as? [String: Any],
           let snapshotData = try? JSONSerialization.data(withJSONObject: params),
           let snapshot = try? JSONDecoder().decode(PendingApprovalsSnapshot.self, from: snapshotData) {
            self.snapshot = snapshot
        }
    }

    private func send<T: Encodable>(_ payload: T) async throws {
        guard let task = socketTask else { return }
        let data = try JSONEncoder().encode(payload)
        guard let text = String(data: data, encoding: .utf8) else { return }
        try await task.send(.string(text))
    }

    private func send(_ payload: [String: Any]) async throws {
        guard let task = socketTask else { return }
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
        guard let text = String(data: data, encoding: .utf8) else { return }
        try await task.send(.string(text))
    }
}
