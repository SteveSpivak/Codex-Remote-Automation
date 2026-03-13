import Foundation

@MainActor
final class ApprovalStore: ObservableObject {
    @Published var phoneDeviceId: String = UUID().uuidString
    @Published var phoneLabel: String = Host.current().localizedName ?? "CRA Operator"
    @Published var pairingText: String = ""
    @Published var noteDrafts: [String: String] = [:]

    let relayClient = RelayClient()

    func connectFromPairingText() async throws {
        let data = Data(pairingText.utf8)
        let payload = try JSONDecoder().decode(PairingPayload.self, from: data)
        try await relayClient.connect(pairingPayload: payload, phoneDeviceId: phoneDeviceId, phoneLabel: phoneLabel)
    }

    func submitDecision(for approval: ApprovalPayload, decision: String) async throws {
        try await relayClient.respondApproval(
            ApprovalDecisionRequest(
                requestId: approval.requestID,
                decision: decision,
                operatorNote: noteDrafts[approval.requestID]
            )
        )
    }
}
