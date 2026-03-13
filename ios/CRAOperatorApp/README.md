# CRA Operator App

Native SwiftUI client for CRA bridge approvals.

This folder contains the app skeleton and shared transport logic for the approval-first v1 client:

- pair from a CRA bridge payload
- connect to the self-hosted relay
- receive pending approvals
- submit `accept`, `acceptForSession`, `decline`, or `cancel`
- optionally attach an operator note for CRA audit

Full Xcode project generation is out of scope in this repo state because this Mac currently has Command Line Tools but not full Xcode. The source layout is ready to be imported into an Xcode iOS app target.
