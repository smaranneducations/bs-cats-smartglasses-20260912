"use strict";

const labels = {
  source_freshness: "Source freshness", record_review: "Exact record review", checkout: "Purchase path",
  publisher_approval: "Publisher approval", product_eligibility: "Product and market eligibility",
  editorial_independence: "Editorial independence", commercial_reuse: "Commercial permissions",
  attribution: "Attribution terms", payment: "Payment terms"
};
const stageLabels = { awaiting_evidence: "Evidence still needed", blocked_by_evidence: "Evidence blocks this path", ready_for_exact_artifact_review: "Ready for artifact review, not publication" };
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
async function load() {
  const status = document.getElementById("status");
  try {
    const response = await fetch("/v1/intelligence/commerce", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error(`Evidence view unavailable (HTTP ${response.status}).`);
    const report = await response.json();
    const assessment = report.assessment;
    document.getElementById("paths").replaceChildren();
    for (const path of assessment.paths) {
      const card = element("article", undefined, "path");
      const head = element("div", undefined, "path-head");
      const title = element("div");
      title.append(element("p", `${path.path_id} / version ${path.path_version}`, "identity"), element("h2", path.title), element("p", path.customer_market, "muted"));
      head.append(title, element("span", stageLabels[path.stage] || path.stage, "stage"));
      const gates = element("ul", undefined, "gates");
      for (const gate of path.gates) {
        const item = element("li", undefined, "gate");
        item.dataset.state = gate.state;
        item.append(element("span", gate.state === "unknown" ? "Not established" : gate.state, "gate-state"), element("h3", labels[gate.gate] || gate.gate), element("p", gate.reason));
        gates.append(item);
      }
      const next = element("div", undefined, "next");
      next.append(element("p", `Agent preparation: ${path.next_agent_action}`), element("p", `Reserved decision: ${path.reserved_human_boundary}`));
      const review = element("a", "Inspect and review the governed objects");
      review.href = "/#review";
      next.append(review);
      card.append(head, gates, next);
      document.getElementById("paths").append(card);
    }
    const sources = document.getElementById("sources");
    sources.replaceChildren();
    for (const source of report.sources) {
      const item = element("li");
      try {
        const url = new URL(source.uri);
        if (url.protocol !== "https:" || url.username || url.password) throw new Error("Not a public web reference");
        const link = element("a", source.title || source.source_id);
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        item.append(link);
      } catch {
        item.textContent = `${source.title || source.source_id}: inspect the private source through object review.`;
      }
      sources.append(item);
    }
    status.textContent = `${assessment.paths.length} governed paths assessed. No tracked links or financial actions are authorized.`;
    document.getElementById("validity").textContent = `Assessed ${new Date(assessment.assessed_at).toLocaleString()}. Reassess by ${new Date(assessment.valid_until).toLocaleString()}. Input changes invalidate this snapshot.`;
  } catch (error) {
    status.textContent = error.message || "The evidence view is unavailable. No readiness conclusion has been made.";
  }
}
load();
