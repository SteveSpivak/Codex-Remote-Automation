import SwiftUI

struct ApprovalDetailView: View {
    @ObservedObject var store: ApprovalStore
    let approval: ApprovalPayload

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(approval.title)
                .font(.title.bold())
            Text(approval.summary)
                .font(.body)
            if approval.operatorNoteEnabled {
                TextField(approval.operatorNotePrompt, text: Binding(
                    get: { store.noteDrafts[approval.requestID, default: ""] },
                    set: { store.noteDrafts[approval.requestID] = $0 }
                ))
                .textFieldStyle(.roundedBorder)
            }
            ForEach(approval.decisionOptions) { option in
                Button(option.label) {
                    Task {
                        try? await store.submitDecision(for: approval, decision: option.value)
                    }
                }
                .buttonStyle(option.value == approval.defaultDecision ? .borderedProminent : .bordered)
            }
        }
        .padding(20)
    }
}
