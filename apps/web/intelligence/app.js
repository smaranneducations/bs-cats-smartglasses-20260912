"use strict";
const $ = (selector) => document.querySelector(selector);
const state = { products: [], definitions: [], selected: new Set(), concepts: new Set(["weight_g", "fov_deg", "refresh_hz"]), overview: null };
function node(tag, text, className) { const item = document.createElement(tag); if (text !== undefined) item.textContent = String(text); if (className) item.className = className; return item; }
function badge(text) { return node("span", text, "badge " + String(text).replace(/[^a-z_]/g, "")); }
function fail(message) { $("#error").textContent = message; $("#error").hidden = false; }
async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options, headers: { "X-Workspace-Action": "1", ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers } });
  if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? "This workspace needs an authorized local session. Credentials are not collected on this page." : "The requested workspace operation could not complete (HTTP " + response.status + ").");
  return response.json();
}
function metric(value, label) { const cell = node("article", undefined, "metric"); cell.append(node("strong", value), node("span", label)); return cell; }
function selectionChanged() {
  $("#compare").disabled = state.selected.size < 2 || state.selected.size > 4 || state.concepts.size === 0;
  $("#selection").textContent = state.selected.size + " product(s) selected. " + state.concepts.size + " concept(s).";
}
function renderProducts() {
  const search = $("#product-search").value.toLowerCase().trim();
  const container = $("#products"); container.replaceChildren();
  for (const product of state.products.filter((item) => [item.title, item.category, item.market].join(" ").toLowerCase().includes(search))) {
    const card = node("article", undefined, "product-card"); const check = node("input"); check.type = "checkbox"; check.checked = state.selected.has(product.object_id); check.setAttribute("aria-label", "Include " + product.title + " in comparison");
    check.addEventListener("change", () => { if (check.checked && state.selected.size >= 4) { check.checked = false; fail("Compare at most four products at a time."); return; } check.checked ? state.selected.add(product.object_id) : state.selected.delete(product.object_id); selectionChanged(); });
    const content = node("div"); content.append(node("h3", product.title), badge("v" + product.version), badge(product.review_state), node("p", product.category + " / " + product.recorded_fields + " recorded fields"), node("p", product.market));
    const button = node("button", "Inspect evidence", "text-button"); button.type = "button"; button.addEventListener("click", () => inspect(product)); card.append(check, content, button); container.append(card);
  }
  if (!container.children.length) container.append(node("p", "No matching product objects.", "empty"));
}
function renderConcepts() {
  const fieldset = $("#concepts"); fieldset.replaceChildren(node("legend", "Concepts to compare"));
  const keys = ["weight_g", "fov_deg", "refresh_hz", "brightness_nits", "resolution", "connection", "phone_support", "battery_hours"];
  for (const definition of state.definitions.filter((item) => keys.includes(item.key))) {
    const label = node("label"); const input = node("input"); input.type = "checkbox"; input.checked = state.concepts.has(definition.key);
    input.addEventListener("change", () => { input.checked ? state.concepts.add(definition.key) : state.concepts.delete(definition.key); selectionChanged(); });
    label.append(input, node("span", definition.label + (definition.unit ? " (" + definition.unit + ")" : ""))); fieldset.append(label);
  }
}
function valueText(assertion) {
  if (!assertion || assertion.value_state === "unknown") return "Unknown";
  const value = assertion.value_boolean !== null && assertion.value_boolean !== undefined ? assertion.value_boolean : assertion.value_number !== null && assertion.value_number !== undefined ? assertion.value_number : assertion.value_text;
  return String(value ?? "Unknown") + (assertion.unit ? " " + assertion.unit : "");
}
function assertionCell(assertion) {
  const cell = node("td"); cell.append(node("strong", valueText(assertion)));
  if (assertion) { cell.append(node("small", assertion.evidence_kind || "Evidence kind unknown"), node("small", "Observed: " + (assertion.observed_at || "Unknown")), node("small", "Confidence: " + (assertion.confidence === null ? "not assessed" : assertion.confidence))); if (assertion.conditions) cell.append(node("small", assertion.conditions)); }
  return cell;
}
function table(headers, rows) {
  const scroll = node("div", undefined, "table-scroll"); scroll.tabIndex = 0; scroll.setAttribute("aria-label", "Scrollable evidence table"); const table = node("table"); const head = node("thead"); const tr = node("tr");
  headers.forEach((name) => { const th = node("th", name); th.scope = "col"; tr.append(th); }); head.append(tr); const body = node("tbody"); rows.forEach((cells) => { const row = node("tr"); cells.forEach((cell) => row.append(cell)); body.append(row); }); table.append(head, body); scroll.append(table); return scroll;
}
function sourceLinks(sources) {
  const links = node("div", undefined, "sources"); const seen = new Set();
  for (const source of sources) { try { const url = new URL(source.uri); if (!["https:", "http:"].includes(url.protocol) || seen.has(url.href)) continue; seen.add(url.href); const a = node("a", source.title || source.publisher || url.hostname); a.href = url.href; a.target = "_blank"; a.rel = "noopener noreferrer"; links.append(a); } catch (_) {} }
  return links;
}
function openInspection(title) { $("#inspection-title").textContent = title; $("#inspection-body").replaceChildren(); $("#inspection").hidden = false; return $("#inspection-body"); }
async function inspect(product) {
  try { const data = await api("/v1/semantic/products/" + encodeURIComponent(product.object_id) + "/assertions"); const body = openInspection(data.title + " / version " + data.version);
    body.append(node("p", data.market + ". " + (data.variant || "Variant not recorded"), "subtle"), node("p", "Recorded knowledge, not independent verification. Product review and publication approval are separate.", "notice"));
    const rows = data.assertions.map((assertion) => { const definition = state.definitions.find((item) => item.concept_id === assertion.concept_id); return [node("td", definition ? definition.label : assertion.concept_id), assertionCell(assertion), node("td", data.human_action_required ? "exception review" : "policy-routed")]; }); body.append(table(["Concept", "Value and conditions", "Governance route"], rows), sourceLinks(data.sources)); $("#inspection").scrollIntoView({ block: "start" });
  } catch (error) { fail(error.message); }
}
async function compare() {
  $("#compare").disabled = true;
  try { const chosen = state.products.filter((item) => state.selected.has(item.object_id)); if (new Set(chosen.map((item) => item.category)).size !== 1) throw new Error("Choose products in the same category. Different categories are not directly rankable.");
    const data = await api("/v1/semantic/compare", { method: "POST", body: JSON.stringify({ product_ids: [...state.selected], concepts: [...state.concepts] }) }); const body = openInspection("A comparison, not an invented ranking"); body.append(node("p", data.caveat, "notice"));
    const rows = data.rows.map((row) => [node("td", row.concept.label), ...row.cells.map((cell) => assertionCell(cell.assertion))]); body.append(table(["Concept", ...data.products.map((item) => item.title)], rows)); data.products.forEach((item) => { body.append(node("p", item.title + ": " + item.market + ". " + (item.variant || "Variant unknown"), "subtle")); }); body.append(sourceLinks(data.products.flatMap((item) => item.sources))); $("#inspection").scrollIntoView({ block: "start" });
  } catch (error) { fail(error.message); } finally { selectionChanged(); }
}
async function inspectRun(taskId) {
  try { const task = await api("/v1/runtime/tasks/" + encodeURIComponent(taskId)); const panel = $("#run-detail"); panel.replaceChildren(node("h3", task.request.objective), badge(task.state), node("p", "Profile: " + task.request.profile_id + " / revision " + task.request.profile_revision, "subtle"), node("p", "Context SHA-256: " + task.context_hash, "subtle"));
    const result = task.result?.result; if (result?.products) { const rows = result.products.map((item) => [node("td", state.products.find((product) => product.object_id === item.object_id)?.title || item.object_id), node("td", item.source_linked_values + " / " + item.applicable_concepts), node("td", item.missing_concepts.join(", ")), node("td", "Not independently verified")]); panel.append(table(["Pinned product", "Source-linked coverage", "Missing concepts", "Evidence boundary"], rows)); }
    const detail = node("details"); detail.append(node("summary", "Inspect pinned context, result and audit trail"), node("pre", JSON.stringify({ inputs: task.request.inputs, acceptance_criteria: task.request.acceptance_criteria, context: task.context, result: task.result, audit: task.audit }, null, 2))); panel.append(detail); panel.hidden = false; panel.scrollIntoView({ block: "start" });
  } catch (error) { fail(error.message); }
}
function renderRuns(tasks) { const container = $("#run-list"); container.replaceChildren(); for (const task of tasks) { const card = node("article", undefined, "run-card"); const info = node("div"); info.append(badge(task.state), node("code", task.task_id), node("p", "Attempts: " + task.attempts + (task.failure_code ? " / " + task.failure_code : "") + " / " + new Date(task.updated_at * 1000).toLocaleString())); const button = node("button", "Inspect execution", "text-button"); button.type = "button"; button.addEventListener("click", () => inspectRun(task.task_id)); card.append(info, button); container.append(card); } if (!tasks.length) container.append(node("p", "No admitted runtime tasks yet. A profile name alone is not an executed worker.", "empty")); }
function renderSystems(data) {
  const cloud = data.cloud_observation; const container = $("#system-list"); container.replaceChildren();
  const entries = [["Knowledge", "Local + versioned", data.counts.objects + " inspectable objects; " + data.counts.concepts + " current concept definitions.", "SQLite object event store"], ["BigQuery", cloud.warehouse.tables_created + " tables created", "Empty schema. No warehouse facts loaded by this implementation; the app does not yet read BigQuery.", cloud.warehouse.dataset + " / " + cloud.warehouse.location], ["Workflow state", "Firestore exists", "The cloud database exists. The application still uses local workflow persistence.", cloud.firestore.database + " / " + cloud.firestore.location], ["Execution", "Bounded workers", "Pinned inputs, leases, retry limits, audit and pause. Local deterministic tools; model providers remain disconnected.", "One active worker"], ["Cloud API", "Not deployed", cloud.cloud_run.services_observed + " services in the last authenticated inventory. Not a laptop-independent deployment.", "Observed " + cloud.observed_on], ["Learning", "Governance captured", "Feedback is retained in project governance. Automatic runtime policy promotion is not connected or implied.", "Permissions cannot self-expand"]];
  for (const [label, title, text, detail] of entries) { const card = node("article", undefined, "system-card"); card.append(node("span", label, "small-label"), node("h3", title), node("p", text), node("code", detail)); container.append(card); }
}
function renderLearning(data) {
  let section = $("#learning");
  if (!section) { section = node("section", undefined, "section"); section.id = "learning"; section.setAttribute("aria-labelledby", "learning-title"); $("#systems").insertAdjacentElement("afterend", section); }
  section.replaceChildren();
  const heading = node("div", undefined, "section-heading"); const title = node("div"); const h2 = node("h2", "Feedback with a traceable outcome."); h2.id = "learning-title"; title.append(node("p", "04 / Governed memory", "eyebrow"), h2); heading.append(title, node("p", "Proposals are not automatically promoted. Reviewed, current, relevant decisions can enter bounded execution context without granting new permissions.")); section.append(heading);
  const list = node("div", undefined, "run-list");
  for (const proposal of data.proposals) {
    const card = node("article", undefined, "run-card"); const body = node("div"); body.append(badge(proposal.review_state), node("h3", proposal.summary), node("code", proposal.object_id + " / v" + proposal.version), node("p", proposal.kind + " / " + (proposal.source_versions_current ? "feedback versions current" : "feedback changed; proposal stale")), node("p", proposal.evaluation));
    const details = node("details"); details.append(node("summary", "Inspect rule scope and source versions"), node("pre", JSON.stringify({ workflow_families: proposal.workflow_families, feedback_versions: proposal.feedback_versions, proposed_rules: proposal.proposed_rules, automatic_promotion: false }, null, 2))); body.append(details);
    const review = node("a", "Open decision review", "text-button"); review.href = "/#review"; card.append(body, review); list.append(card);
  }
  if (!data.proposals.length) list.append(node("p", "No typed learning proposals are recorded yet.", "empty")); section.append(list);
  const learningCard = [...$("#system-list").children].find((card) => card.querySelector(".small-label")?.textContent === "Learning");
  if (learningCard) { learningCard.querySelector("h3").textContent = "Governed memory"; learningCard.querySelector("p").textContent = "Versioned feedback proposals, human-reviewed scoped context and downstream impact tracking. No automatic ontology migration or permission expansion."; }
}
async function load() {
  $("#error").hidden = true; $("#reload").disabled = true;
  try { const data = await api("/v1/intelligence/overview"); const ontology = await api("/v1/semantic/ontology"); const runs = await api("/v1/runtime/tasks"); state.overview = data; state.products = data.products; state.definitions = ontology.items;
    const valid = new Set(state.products.map((item) => item.object_id)); state.selected = new Set([...state.selected].filter((id) => valid.has(id)));
    $("#metrics").replaceChildren(metric(data.products.length, "product objects"), metric(data.counts.concepts, "semantic concepts"), metric(data.runtime.tasks_by_state.completed || 0, "completed deterministic jobs"), metric("Unknown", "collected revenue"));
    renderProducts(); renderConcepts(); selectionChanged(); renderRuns(runs.tasks); renderSystems(data);
    renderLearning(await api("/v1/intelligence/learning"));
    $("#budget").textContent = "$" + (data.runtime.owner_reported_subscription_cents / 100).toFixed(0) + " subscription reported once. $" + (data.runtime.ceiling_cents / 100).toFixed(0) + " cumulative experiment ceiling. Other charges are unreconciled; spendable headroom is unknown and paid jobs remain disabled.";
    $("#connection").textContent = "Local data loaded / " + new Date().toLocaleTimeString();
  } catch (error) { fail(error.message); $("#connection").textContent = "Workspace data could not be loaded."; } finally { $("#reload").disabled = false; }
}
$("#reload").addEventListener("click", load); $("#product-search").addEventListener("input", renderProducts); $("#compare").addEventListener("click", compare); $("#close-inspection").addEventListener("click", () => { $("#inspection").hidden = true; }); load();
