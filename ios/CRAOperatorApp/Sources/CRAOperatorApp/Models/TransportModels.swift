import Foundation

struct PairingPayload: Codable {
    let v: Int
    let protocolVersion: Int
    let relayUrl: String
    let sessionId: String
    let bridgeDeviceId: String
    let pairingSecret: String
    let expiresAt: Int
}

struct ClientHello: Codable {
    let kind = "clientHello"
    let protocolVersion: Int
    let sessionId: String
    let handshakeMode: String
    let phoneDeviceId: String
    let phoneLabel: String?
    let clientNonce: String
    let clientProof: String
}

struct ServerHello: Codable {
    let kind: String
    let protocolVersion: Int
    let sessionId: String
    let handshakeMode: String
    let bridgeDeviceId: String
    let serverNonce: String
    let keyEpoch: Int
    let bridgeProof: String
}

struct ClientAuth: Codable {
    let kind = "clientAuth"
    let sessionId: String
    let phoneDeviceId: String
    let keyEpoch: Int
    let clientAuth: String
}

struct ResumeState: Codable {
    let kind = "resumeState"
    let sessionId: String
    let keyEpoch: Int
    let lastAppliedBridgeOutboundSeq: Int
}

struct EncryptedEnvelope: Codable {
    let kind: String
    let v: Int
    let sessionId: String
    let keyEpoch: Int
    let sender: String
    let counter: Int
    let ciphertext: String
    let tag: String
}
