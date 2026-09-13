"use strict";
(async () => {
  const select = (value) => document.querySelector(value);
  try {
    const id = decodeURIComponent(location.pathname.split("/").pop());
    if (!/^render_[0-9a-f]{32}$/.test(id)) throw new Error("Choose a valid governed render artifact.");
    const base = "/v1/media/artifacts/" + encodeURIComponent(id);
    const response = await fetch(base, {credentials:"same-origin"});
    if (!response.ok) throw new Error("The private artifact is unavailable in this authorized session.");
    const data = await response.json();
    select("#title").textContent = data.title;
    select("#status").textContent = data.payload.duration_seconds + " seconds / background music / review: " + data.review_state;
    select("#video").src = base + "/video";
    select("#video").poster = base + "/poster";
    select("#metadata").textContent = JSON.stringify(data.payload.publish_metadata,null,2);
    select("#identity").textContent = JSON.stringify({object_id:data.object_id,version:data.version,recipe_id:data.payload.recipe_object_id,video_sha256:data.payload.video_sha256,metadata_sha256:data.payload.metadata_sha256,publication_allowed:false},null,2);
    for (const source of data.sources) { const url = new URL(source.uri); if (!["https:","http:"].includes(url.protocol)) continue; const link = document.createElement("a"); link.href=url.href; link.textContent=source.title || source.publisher || url.hostname; link.target="_blank"; link.rel="noopener noreferrer"; select("#sources").append(link); }
    const manifestResponse = await fetch(base + "/manifest", {credentials:"same-origin"});
    if (!manifestResponse.ok) throw new Error("The manifest identity could not be established.");
    select("#manifest").textContent = JSON.stringify(await manifestResponse.json(),null,2);
  } catch (error) { document.querySelector("#error").textContent=error.message; document.querySelector("#error").hidden=false; }
})();

// A separate evidence panel; it cannot approve or publish the video.
(() => {
  const match = location.pathname.match(/^\/media-review\/(render_[a-z0-9]+)$/);
  if (!match) return;
  const panel = document.createElement("section");
  panel.className = "release-readiness";
  const heading = document.createElement("h2");
  heading.textContent = "Release checks";
  const note = document.createElement("p");
  note.textContent = "Checking this video's bytes, lineage and separate review gates...";
  const refresh = document.createElement("button");
  refresh.type = "button";
  refresh.textContent = "Refresh evidence";
  const list = document.createElement("dl");
  panel.append(heading, note, refresh, list);
  (document.querySelector("main") || document.body).append(panel);
  async function update() {
    refresh.disabled = true;
    try {
      const response = await fetch(`/v1/media/artifacts/${match[1]}/release-review`, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error(`Release evidence unavailable (HTTP ${response.status}).`);
      const { packet } = await response.json();
      list.replaceChildren();
      for (const check of packet.checks) {
        const term = document.createElement("dt");
        term.textContent = `${check.check_id.replaceAll("_", " ")} / ${check.state.replaceAll("_", " ")}`;
        term.dataset.state = check.state;
        const description = document.createElement("dd");
        description.textContent = check.reason;
        list.append(term, description);
      }
      note.textContent = `${packet.summary} Checked ${new Date(packet.checked_at).toLocaleString()}. Human viewing/listening review and all publishing permissions remain separate.`;
    } catch (error) {
      note.textContent = error.message || "No release-readiness conclusion is available.";
      list.replaceChildren();
    } finally {
      refresh.disabled = false;
    }
  }
  refresh.addEventListener("click", update);
  update();
})();
