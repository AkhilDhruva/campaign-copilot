import { useState } from "react";
import type { CopyDraft, Issue } from "../types";

/** Wrap every flagged snippet in a <mark>, so the reader sees exactly what was caught. */
function highlight(text: string, snippets: string[]): (string | JSX.Element)[] {
  const probes = snippets.map((s) => s.trim()).filter((s) => s.length > 3);
  if (probes.length === 0) return [text];
  const escaped = probes.map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.split(re).map((part, i) =>
    probes.some((p) => p.toLowerCase() === part.toLowerCase()) ? (
      <mark key={i}>{part}</mark>
    ) : (
      part
    ),
  );
}

function Piece({
  title,
  text,
  issues,
}: {
  title: string;
  text: string;
  issues: Issue[];
}) {
  const snippets = issues.map((i) => i.snippet);
  return (
    <section className="piece">
      <header>
        <h4>{title}</h4>
        {issues.length > 0 && <span className="pill bad">{issues.length} flagged</span>}
      </header>
      <pre>{highlight(text, snippets)}</pre>
    </section>
  );
}

export function CopyView({
  drafts,
  issuesByDraft,
  citations,
}: {
  drafts: CopyDraft[];
  issuesByDraft: Issue[][];
  citations: string[];
}) {
  const [idx, setIdx] = useState(drafts.length - 1);
  const draft = drafts[Math.min(idx, drafts.length - 1)];
  const issues = issuesByDraft[Math.min(idx, drafts.length - 1)] ?? [];
  if (!draft) return null;
  const byPiece = (piece: string) => issues.filter((i) => i.piece === piece);

  return (
    <div className="copyview">
      <div className="draft-tabs">
        {drafts.map((_, i) => (
          <button key={i} className={i === idx ? "active" : ""} onClick={() => setIdx(i)}>
            {i === 0 ? "First draft" : `Revision ${i}`}
            {(issuesByDraft[i]?.length ?? 0) > 0 ? ` · ${issuesByDraft[i].length} issues` : " · clean"}
          </button>
        ))}
      </div>

      {issues.length > 0 && (
        <ul className="issues">
          {issues.map((i) => (
            <li key={i.id} className={i.severity}>
              <strong>
                {i.id} {i.severity === "block" ? "BLOCK" : "warn"}
              </strong>{" "}
              {i.message} <em>{i.citation}</em>
              {i.fix && <div className="fix">Fix: {i.fix}</div>}
            </li>
          ))}
        </ul>
      )}

      <Piece title="Direct-mail letter" text={draft.letter} issues={byPiece("letter")} />
      <Piece
        title="Email"
        text={`Subject: ${draft.email_subject}\n\n${draft.email_body}`}
        issues={byPiece("email")}
      />
      <div className="ads">
        {draft.ads.map((ad, n) => (
          <Piece
            key={n}
            title={`Digital ad ${n + 1}`}
            text={`${ad.headline}\n${ad.body}`}
            issues={byPiece(`ad_${n + 1}`)}
          />
        ))}
      </div>

      <section className="citations">
        <h4>What drove these choices</h4>
        <ul>
          {(draft.data_citations.length ? draft.data_citations : citations).map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
