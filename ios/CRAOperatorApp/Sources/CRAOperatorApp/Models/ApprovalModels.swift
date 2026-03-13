import Foundation

struct DecisionOption: Codable, Identifiable, Hashable {
    let value: String
    let label: String

    var id: String { value }
}

struct ApprovalPayload: Codable, Identifiable, Hashable {
    let title: String
    let subtitle: String
    let requestID: String
    let threadID: String
    let turnID: String
    let itemID: String
    let kind: String
    let summary: String
    let timestamp: String
    let decisionOptions: [DecisionOption]
    let defaultDecision: String
    let operatorNoteEnabled: Bool
    let operatorNotePrompt: String

    enum CodingKeys: String, CodingKey {
        case title
        case subtitle
        case requestID = "request_id"
        case threadID = "thread_id"
        case turnID = "turn_id"
        case itemID = "item_id"
        case kind
        case summary
        case timestamp
        case decisionOptions = "decision_options"
        case defaultDecision = "default_decision"
        case operatorNoteEnabled = "operator_note_enabled"
        case operatorNotePrompt = "operator_note_prompt"
    }

    var id: String { requestID }
}

struct PendingApprovalsSnapshot: Codable, Hashable {
    let pendingApprovals: [ApprovalPayload]
    let pendingCount: Int
    let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case pendingApprovals = "pendingApprovals"
        case pendingCount = "pendingCount"
        case updatedAt = "updatedAt"
    }
}

struct ApprovalDecisionRequest: Codable {
    let requestId: String
    let decision: String
    let operatorNote: String?
}
