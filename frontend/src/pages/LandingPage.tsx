import {
  ArrowRight,
  ClipboardCheck,
  FileSearch,
  MessageSquareText,
  Network,
  ShieldCheck,
  UsersRound
} from "lucide-react";
import { Link } from "react-router-dom";
import "../styles/landing.css";

const workflowTools = [
  {
    number: "01",
    title: "Log Complaint",
    description: "Natural-language complaint intake that automatically populates the structured quality record.",
    icon: MessageSquareText
  },
  {
    number: "02",
    title: "Edit Complaint",
    description: "Correct any field through chat while preserving every unrelated value.",
    icon: ClipboardCheck
  },
  {
    number: "03",
    title: "Document Extraction",
    description: "Extract complaint details and source evidence from PDF, DOCX, TXT, and EML files.",
    icon: FileSearch
  }
];

const supportingIntelligence = [
  {
    title: "Evidence Lock",
    description: "Trace every value to its source, excerpt, page, confidence, and correction history."
  },
  {
    title: "Safety Router",
    description: "Identify quality complaints, possible adverse events, counterfeit concerns, and distribution issues."
  },
  {
    title: "Investigation Playbooks",
    description: "Generate defect-specific containment, investigation, root-cause, and CAPA considerations."
  },
  {
    title: "Inspector Replay",
    description: "Replay the complete complaint lifecycle through an ordered and auditable timeline."
  }
];

const processSteps = [
  "Submit Complaint",
  "AI Extracts and Validates",
  "Risk and Safety Triage",
  "Batch Impact Analysis",
  "Quality War Room",
  "Human QA Review",
  "QMS Ledger"
];

const safetyItems = [
  "Read-only complaint record",
  "Patch-based edits",
  "Original evidence preservation",
  "Field-level audit events",
  "Versioned risk assessments",
  "Human approval before saving",
  "No automatic recall or regulatory submission"
];

export function LandingPage() {
  return (
    <main className="landing-page" data-font-family="Inter">
      <header className="landing-nav" aria-label="PharmaQ Sentinel navigation">
        <Link className="landing-brand" to="/">
          PharmaQ Sentinel
        </Link>
        <nav className="landing-nav__links" aria-label="Landing page sections">
          <a href="#product">Product</a>
          <a href="#how-it-works">How It Works</a>
          <a href="#quality-intelligence">Quality Intelligence</a>
          <a href="#compliance">Compliance</a>
        </nav>
        <Link className="button button--primary" to="/workspace">
          Open Workspace
        </Link>
      </header>

      <section className="landing-hero" id="product">
        <div className="landing-hero__content">
          <span className="landing-pill">Built for API and FDF manufacturers</span>
          <h1>From customer complaint to quality intelligence in minutes.</h1>
          <p>
            PharmaQ Sentinel converts unstructured pharmaceutical complaints into structured,
            evidence-backed quality records, assesses patient and batch impact, and prepares an
            auditable review package for QA teams.
          </p>
          <div className="landing-actions">
            <Link className="button button--primary" to="/workspace">
              Launch Complaint Workspace
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <a className="button button--secondary" href="#how-it-works">
              View How It Works
            </a>
          </div>
        </div>

        <div className="landing-flow-card" aria-label="Complaint intelligence workflow preview">
          {["Complaint", "AI Extraction", "Risk Review", "Batch Intelligence", "QA Decision"].map((step) => (
            <div className="landing-flow-step" key={step}>
              <span>{step}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" id="how-it-works">
        <div className="landing-section__heading">
          <span>Mandatory Workflow</span>
          <h2>One assistant. One controlled complaint record.</h2>
          <p>
            All form fields remain read-only. Every update happens through the AI assistant.
          </p>
        </div>
        <div className="landing-tool-grid">
          {workflowTools.map((tool) => {
            const Icon = tool.icon;
            return (
              <article className="landing-tool-card" key={tool.title}>
                <div className="landing-card-icon" aria-hidden="true">
                  <Icon size={18} />
                </div>
                <span>{tool.number}</span>
                <h3>{tool.title}</h3>
                <p>{tool.description}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="landing-section" id="quality-intelligence">
        <div className="landing-section__heading">
          <span>Quality Intelligence</span>
          <h2>Standout tools for connected quality review.</h2>
        </div>
        <div className="landing-feature-grid">
          <article className="landing-feature-card">
            <Network size={22} aria-hidden="true" />
            <h3>Batch Blast-Radius Digital Twin</h3>
            <p>
              Trace a complaint across connected batches, raw materials, packaging lots, equipment,
              deviations, CAPAs, distribution locations, and remaining inventory.
            </p>
            <div className="landing-metric-row" aria-label="Batch intelligence signals">
              <span>Related batches</span>
              <span>Open deviations</span>
              <span>Distributed markets</span>
              <span>Inventory at risk</span>
            </div>
            <Link className="button button--secondary" to="/workspace?tab=batch-intelligence">
              Explore Batch Intelligence
            </Link>
          </article>

          <article className="landing-feature-card">
            <UsersRound size={22} aria-hidden="true" />
            <h3>AI Quality War Room</h3>
            <p>
              A multidisciplinary AI review involving QA, manufacturing, packaging, supplier quality,
              pharmacovigilance, and a compliance auditor.
            </p>
            <div className="landing-chip-row" aria-label="War room agents">
              <span>QA Risk</span>
              <span>Manufacturing</span>
              <span>Packaging</span>
              <span>Pharmacovigilance</span>
              <span>Compliance Auditor</span>
            </div>
            <Link className="button button--secondary" to="/workspace?tab=quality-war-room">
              View Quality War Room
            </Link>
          </article>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-support-grid">
          {supportingIntelligence.map((item) => (
            <article className="landing-support-card" key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-process">
        <div className="landing-section__heading">
          <span>Review Flow</span>
          <h2>AI recommends. Authorised QA personnel review and approve.</h2>
        </div>
        <ol>
          {processSteps.map((step, index) => (
            <li key={step}>
              <span>{index + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-section landing-safety" id="compliance">
        <div>
          <ShieldCheck size={22} aria-hidden="true" />
          <h2>Designed around traceability and human review</h2>
          <p>Designed to support controlled pharmaceutical quality workflows.</p>
        </div>
        <ul>
          {safetyItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="landing-final-cta">
        <h2>Ready to investigate a complaint?</h2>
        <Link className="button button--primary" to="/workspace">
          Launch Complaint Workspace
        </Link>
        <p>Use fictional demonstration data only. AI-generated recommendations require QA review.</p>
      </section>

      <footer className="landing-footer">
        <span>PharmaQ Sentinel</span>
        <span>AI assistance for pharmaceutical quality review, with human authorization retained.</span>
      </footer>
    </main>
  );
}
