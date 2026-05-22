"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon, I } from "@/lib/icons";
import {
  buildCompetitorIntelQuery,
  canRunTarget,
  competitorIntelRunPayload,
  displayValue,
  formatBoolean,
  formatDate,
  formatInteger,
  formatPercent,
  formatTargetLabel,
  hasTarget,
  normalizeCompetitorIntelState,
} from "@/lib/competitor-intel/format";
import {
  COMPETITOR_INTEL_SCAN_COST,
  type AggregateOnlyIntel,
  type CompetitorIntelAccount,
  type CompetitorIntelApiEnvelope,
  type CompetitorIntelReport,
  type CompetitorIntelTarget,
  type CompetitorIntelViewState,
  type CoverageFact,
  type LocalPackCompetitor,
  type OrganicCompetitor,
} from "@/lib/competitor-intel/types";

interface CompetitorIntelClientProps {
  account: CompetitorIntelAccount;
  target: CompetitorIntelTarget;
  initialState?: CompetitorIntelViewState;
}

function initialViewState(
  account: CompetitorIntelAccount,
  target: CompetitorIntelTarget,
): CompetitorIntelViewState {
  if (account.plan_key === "free" || account.monthly_report_limit <= 0) {
    return {
      kind: "upgrade_required",
      message: "Competitor Intel is available on Plus and Pro plans.",
    };
  }
  if (!hasTarget(target)) {
    return {
      kind: "ready_to_run",
      message: "Add a city and service, or open this page from a saved report.",
    };
  }
  return { kind: "ready_to_run" };
}

function SectionTitle({
  id,
  title,
  meta,
}: {
  id: string;
  title: string;
  meta?: string;
}) {
  return (
    <div className="competitor-section-title">
      <h2 id={id}>{title}</h2>
      {meta ? <span>{meta}</span> : null}
    </div>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail?: string | null }) {
  return (
    <div className="competitor-metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function FactPill({ label, value }: { label: string; value: string | null }) {
  if (!value || value === "Missing") return null;
  return (
    <span className="competitor-fact-pill">
      <span>{label}</span>
      {value}
    </span>
  );
}

function EmptyEvidence({ children }: { children: React.ReactNode }) {
  return <div className="competitor-empty-evidence">{children}</div>;
}

function MarketLedger({ report }: { report: CompetitorIntelReport | AggregateOnlyIntel }) {
  const visible = report.market_ledger.filter((item) => displayValue(item.value) !== "Missing");
  return (
    <section className="competitor-panel" aria-labelledby="competitor-ledger">
      <SectionTitle id="competitor-ledger" title="Market ledger" />
      {visible.length > 0 ? (
        <div className="competitor-ledger-grid">
          {visible.map((item) => (
            <MetricCard
              key={`${item.label}:${displayValue(item.value)}`}
              label={item.label}
              value={displayValue(item.value)}
              detail={item.detail}
            />
          ))}
        </div>
      ) : (
        <EmptyEvidence>Market ledger facts have not been returned yet.</EmptyEvidence>
      )}
    </section>
  );
}

function SummaryMetrics({ report }: { report: CompetitorIntelReport | AggregateOnlyIntel }) {
  const visible = report.summary_metrics.filter((item) => displayValue(item.value) !== "Missing");
  return (
    <section className="competitor-panel" aria-labelledby="competitor-summary">
      <SectionTitle id="competitor-summary" title="Summary metrics" />
      {visible.length > 0 ? (
        <div className="competitor-summary-grid">
          {visible.map((metric) => (
            <MetricCard
              key={`${metric.label}:${displayValue(metric.value)}`}
              label={metric.label}
              value={displayValue(metric.value)}
              detail={metric.detail}
            />
          ))}
        </div>
      ) : (
        <EmptyEvidence>Summary metrics are still pending for this market.</EmptyEvidence>
      )}
    </section>
  );
}

function OrganicCompetitorCard({ competitor }: { competitor: OrganicCompetitor }) {
  return (
    <article className="competitor-row-card">
      <div className="competitor-row-main">
        <div className="competitor-rank">#{competitor.rank ?? "?"}</div>
        <div className="competitor-row-copy">
          <h3>{competitor.domain}</h3>
          {competitor.title ? <p>{competitor.title}</p> : null}
          <div className="competitor-fact-row">
            <FactPill label="DA" value={competitor.domain_authority === null || competitor.domain_authority === undefined ? null : formatInteger(competitor.domain_authority)} />
            <FactPill label="Backlinks" value={competitor.backlink_count === null || competitor.backlink_count === undefined ? null : formatInteger(competitor.backlink_count)} />
            <FactPill label="Ref domains" value={competitor.referring_domains === null || competitor.referring_domains === undefined ? null : formatInteger(competitor.referring_domains)} />
            <FactPill label="Lighthouse" value={competitor.lighthouse_score === null || competitor.lighthouse_score === undefined ? null : formatInteger(competitor.lighthouse_score)} />
            <FactPill label="Schema" value={competitor.schema_adoption === null || competitor.schema_adoption === undefined ? null : formatBoolean(competitor.schema_adoption)} />
          </div>
        </div>
      </div>
      {competitor.weaknesses && competitor.weaknesses.length > 0 ? (
        <ul className="competitor-evidence-list">
          {competitor.weaknesses.slice(0, 3).map((weakness) => (
            <li key={weakness}>{weakness}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

function OrganicCompetitors({ competitors }: { competitors: OrganicCompetitor[] }) {
  return (
    <section className="competitor-panel" aria-labelledby="competitor-organic">
      <SectionTitle
        id="competitor-organic"
        title="Organic competitors"
        meta={`${competitors.length} ranked`}
      />
      {competitors.length > 0 ? (
        <div className="competitor-list">
          {competitors.map((competitor) => (
            <OrganicCompetitorCard
              key={`${competitor.rank ?? "rank"}:${competitor.domain}`}
              competitor={competitor}
            />
          ))}
        </div>
      ) : (
        <EmptyEvidence>No organic competitor rows were returned.</EmptyEvidence>
      )}
    </section>
  );
}

function LocalPackCompetitorCard({ competitor }: { competitor: LocalPackCompetitor }) {
  return (
    <article className="competitor-row-card">
      <div className="competitor-row-main">
        <div className="competitor-rank">#{competitor.rank ?? "?"}</div>
        <div className="competitor-row-copy">
          <h3>{competitor.name}</h3>
          <div className="competitor-fact-row">
            <FactPill label="Rating" value={competitor.rating === null || competitor.rating === undefined ? null : competitor.rating.toFixed(1)} />
            <FactPill label="Reviews" value={competitor.review_count === null || competitor.review_count === undefined ? null : formatInteger(competitor.review_count)} />
            <FactPill label="GBP" value={competitor.gbp_completeness === null || competitor.gbp_completeness === undefined ? null : formatPercent(competitor.gbp_completeness)} />
          </div>
        </div>
      </div>
      {competitor.weaknesses && competitor.weaknesses.length > 0 ? (
        <ul className="competitor-evidence-list">
          {competitor.weaknesses.slice(0, 3).map((weakness) => (
            <li key={weakness}>{weakness}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

function LocalPackCompetitors({ competitors }: { competitors: LocalPackCompetitor[] }) {
  return (
    <section className="competitor-panel" aria-labelledby="competitor-local-pack">
      <SectionTitle
        id="competitor-local-pack"
        title="Local-pack competitors"
        meta={`${competitors.length} visible`}
      />
      {competitors.length > 0 ? (
        <div className="competitor-list">
          {competitors.map((competitor) => (
            <LocalPackCompetitorCard
              key={`${competitor.rank ?? "rank"}:${competitor.name}`}
              competitor={competitor}
            />
          ))}
        </div>
      ) : (
        <EmptyEvidence>No local-pack competitor rows were returned.</EmptyEvidence>
      )}
    </section>
  );
}

function WinPlan({ report }: { report: CompetitorIntelReport }) {
  return (
    <section className="competitor-panel" aria-labelledby="competitor-win-plan">
      <SectionTitle id="competitor-win-plan" title="Win plan" meta={`${report.win_plan.length} plays`} />
      {report.win_plan.length > 0 ? (
        <div className="competitor-play-list">
          {report.win_plan.map((play, index) => (
            <article key={`${play.title}:${index}`} className="competitor-play">
              <div className="competitor-play-index">{index + 1}</div>
              <div>
                <div className="competitor-play-head">
                  <h3>{play.title}</h3>
                  {play.estimated_impact ? <span>{play.estimated_impact} impact</span> : null}
                </div>
                <p>{play.play}</p>
                {play.rationale ? <small>{play.rationale}</small> : null}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyEvidence>No win-plan plays were generated.</EmptyEvidence>
      )}
    </section>
  );
}

function CoveragePanel({ coverage }: { coverage: CoverageFact[] }) {
  const facts = coverage.length > 0 ? coverage : [
    { label: "Competitor facts", status: "missing" as const, detail: "No coverage metadata returned." },
  ];
  return (
    <section className="competitor-panel" aria-labelledby="competitor-coverage">
      <SectionTitle id="competitor-coverage" title="Coverage" />
      <div className="competitor-coverage-list">
        {facts.map((fact) => (
          <div key={`${fact.label}:${fact.status}`} className={`competitor-coverage-item ${fact.status}`}>
            <span>{fact.status.replace("_", " ")}</span>
            <strong>{fact.label}</strong>
            {fact.detail ? <small>{fact.detail}</small> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function UpgradeRequired({ message }: { message?: string }) {
  return (
    <section className="competitor-state-panel" aria-labelledby="competitor-upgrade-title">
      <div className="kicker">Upgrade required</div>
      <h2 id="competitor-upgrade-title">Competitor Intel needs a paid plan.</h2>
      <p>{message ?? "Free accounts can view cached reports, but fresh competitor dossiers require Plus or Pro."}</p>
      <Link href="/settings" className="btn-primary competitor-action-link">
        View plans <Icon d={I.arrow} />
      </Link>
    </section>
  );
}

function ReadyToRun({
  account,
  target,
  message,
  confirming,
  onAskConfirm,
  onCancel,
  onConfirm,
}: {
  account: CompetitorIntelAccount;
  target: CompetitorIntelTarget;
  message?: string;
  confirming: boolean;
  onAskConfirm: () => void;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const runnable = canRunTarget(target);
  const hasEnoughScans = account.fresh_reports_remaining >= COMPETITOR_INTEL_SCAN_COST;
  return (
    <section className="competitor-state-panel" aria-labelledby="competitor-ready-title">
      <div className="kicker">Ready to run</div>
      <h2 id="competitor-ready-title">{formatTargetLabel(target)}</h2>
      <p>
        {message ??
          "Run competitor intelligence when this market is worth a deeper SERP and local-pack read."}
      </p>
      <div className="competitor-cost-grid" aria-label="Competitor Intel scan cost">
        <MetricCard label="Cost" value={`${COMPETITOR_INTEL_SCAN_COST} scans`} detail="Charged before the run starts" />
        <MetricCard label="Scans remaining" value={formatInteger(account.fresh_reports_remaining)} detail={account.plan_label} />
      </div>
      {!runnable ? (
        <p className="competitor-inline-warning" role="status">
          Open this route with report_id, or city and service query params.
        </p>
      ) : null}
      {!hasEnoughScans ? (
        <p className="competitor-inline-warning" role="status">
          You need 2 scans remaining to run Competitor Intel.
        </p>
      ) : null}
      {!confirming ? (
        <button
          type="button"
          className="btn-primary"
          disabled={!runnable || !hasEnoughScans}
          onClick={onAskConfirm}
        >
          <Icon d={I.target} />
          Run Competitor Intel
        </button>
      ) : (
        <div
          role="alertdialog"
          aria-labelledby="competitor-confirm-title"
          aria-describedby="competitor-confirm-copy"
          className="competitor-confirm"
        >
          <div>
            <h3 id="competitor-confirm-title">Confirm 2-scan run</h3>
            <p id="competitor-confirm-copy">
              This will use 2 of your remaining scans for {formatTargetLabel(target)}.
            </p>
          </div>
          <div className="competitor-confirm-actions">
            <button type="button" className="btn-ghost" onClick={onCancel}>
              Cancel
            </button>
            <button type="button" className="btn-primary" onClick={onConfirm}>
              Confirm run
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function RunningState({ state }: { state: Extract<CompetitorIntelViewState, { kind: "running" }> }) {
  return (
    <section className="competitor-state-panel" aria-labelledby="competitor-running-title">
      <div className="kicker">Running</div>
      <h2 id="competitor-running-title">Competitor Intel is in progress.</h2>
      <p role="status">{state.message ?? "The run has started. Refresh shortly for the completed dossier."}</p>
      <div className="competitor-progress" aria-hidden="true">
        <span />
      </div>
      {state.run_id ? <small>Run {state.run_id}</small> : null}
    </section>
  );
}

function AggregateOnlyState({
  aggregate,
  message,
}: {
  aggregate: AggregateOnlyIntel;
  message?: string;
}) {
  return (
    <div className="competitor-stack" data-state="aggregate_only">
      <section className="competitor-state-panel">
        <div className="kicker">Aggregate only</div>
        <h2>Market-level evidence is available.</h2>
        <p>
          {message ??
            aggregate.message ??
            "This market has enough aggregate evidence to guide a decision, but competitor-level rows are not complete yet."}
        </p>
      </section>
      <MarketLedger report={aggregate} />
      <SummaryMetrics report={aggregate} />
      <CoveragePanel coverage={aggregate.coverage} />
    </div>
  );
}

function DossierState({ report }: { report: CompetitorIntelReport }) {
  return (
    <div className="competitor-stack" data-state="dossier">
      <div className="competitor-dossier-meta">
        <span>{[report.city, report.state].filter(Boolean).join(", ")}</span>
        <span>{report.service}</span>
        <span>Generated {formatDate(report.generated_at)}</span>
      </div>
      <MarketLedger report={report} />
      <SummaryMetrics report={report} />
      <OrganicCompetitors competitors={report.organic_competitors} />
      <LocalPackCompetitors competitors={report.local_pack_competitors} />
      <WinPlan report={report} />
      <CoveragePanel coverage={report.coverage} />
    </div>
  );
}

export default function CompetitorIntelClient({
  account,
  target,
  initialState,
}: CompetitorIntelClientProps) {
  const [state, setState] = useState<CompetitorIntelViewState>(
    () => initialState ?? initialViewState(account, target),
  );
  const [confirming, setConfirming] = useState(false);

  const targetQuery = useMemo(() => buildCompetitorIntelQuery(target), [target]);
  const targetHasContext = useMemo(() => hasTarget(target), [target]);

  useEffect(() => {
    if (initialState || account.plan_key === "free" || !targetHasContext) return;
    let cancelled = false;

    async function loadReport() {
      try {
        const response = await fetch(`/api/competitor-intel?${targetQuery}`);
        const body = (await response.json().catch(() => ({}))) as CompetitorIntelApiEnvelope;
        if (cancelled) return;
        if (!response.ok) {
          setState({
            kind: "error",
            message: body.message ?? `Competitor Intel failed to load (HTTP ${response.status}).`,
          });
          return;
        }
        setState(normalizeCompetitorIntelState(body));
      } catch (error) {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Competitor Intel failed to load.",
          });
        }
      }
    }

    loadReport();
    return () => {
      cancelled = true;
    };
  }, [account.plan_key, initialState, targetHasContext, targetQuery]);

  const runIntel = useCallback(async () => {
    setConfirming(false);
    setState({ kind: "running", message: "Starting competitor intelligence..." });
    try {
      const response = await fetch("/api/competitor-intel/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(competitorIntelRunPayload(target)),
      });
      const body = (await response.json().catch(() => ({}))) as CompetitorIntelApiEnvelope;
      if (!response.ok) {
        setState(normalizeCompetitorIntelState({
          status: body.status ?? "error",
          message: body.message ?? `Competitor Intel run failed (HTTP ${response.status}).`,
          ...body,
        }));
        return;
      }
      setState(normalizeCompetitorIntelState(body));
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof Error ? error.message : "Competitor Intel run failed.",
      });
    }
  }, [target]);

  return (
    <div className="competitor-shell">
      <header className="competitor-hero">
        <div className="competitor-hero-icon" aria-hidden="true">
          <Icon d={I.target} size={22} />
        </div>
        <div>
          <div className="kicker">Competitor intelligence</div>
          <h1 className="page-h1">Competitor Intel</h1>
          <p className="page-sub">
            A compact dossier for who ranks, where they are weak, and what to do first.
          </p>
        </div>
      </header>

      {state.kind === "upgrade_required" ? (
        <UpgradeRequired message={state.message} />
      ) : state.kind === "ready_to_run" ? (
        <ReadyToRun
          account={account}
          target={target}
          message={state.message}
          confirming={confirming}
          onAskConfirm={() => setConfirming(true)}
          onCancel={() => setConfirming(false)}
          onConfirm={runIntel}
        />
      ) : state.kind === "running" ? (
        <RunningState state={state} />
      ) : state.kind === "aggregate_only" ? (
        <AggregateOnlyState aggregate={state.aggregate} message={state.message} />
      ) : state.kind === "dossier" ? (
        <DossierState report={state.report} />
      ) : (
        <section className="competitor-state-panel" role="alert">
          <div className="kicker">Error</div>
          <h2>Competitor Intel is unavailable.</h2>
          <p>{state.message}</p>
          <button type="button" className="btn-ghost" onClick={() => setState(initialViewState(account, target))}>
            Reset
          </button>
        </section>
      )}
    </div>
  );
}
