import SwiftUI

struct ApprovalListView: View {
    @ObservedObject var store: ApprovalStore

    var body: some View {
        NavigationStack {
            List(store.relayClient.snapshot?.pendingApprovals ?? []) { approval in
                NavigationLink(destination: ApprovalDetailView(store: store, approval: approval)) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(approval.subtitle.capitalized)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                        Text(approval.summary)
                            .font(.body)
                            .lineLimit(3)
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle("CRA Approvals")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Text(store.relayClient.status)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}
