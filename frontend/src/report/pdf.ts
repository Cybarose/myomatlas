import { jsPDF } from "jspdf";
import {
  BLEEDING_LABEL,
  FERTILITY_LABEL,
  MENOPAUSAL_LABEL,
  isIntakeProvided,
} from "../api/intake";
import type { CaseReport, ClinicalIntake, MyomaDetail } from "../types";

// A4 in points, with a print-safe margin. Black on white, one standard family, so the
// document prints cleanly and carries none of the dark screen theme.
const PAGE_WIDTH = 595.28;
const PAGE_HEIGHT = 841.89;
const MARGIN = 56;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;
const BOTTOM = PAGE_HEIGHT - MARGIN - 24;

const INK = 20;
const MUTED = 105;
const RULE = 200;

const DISCLAIMER =
  "This report is decision support, not a diagnosis. A clinician makes the final " +
  "diagnosis and treatment decision.";

interface Layout {
  doc: jsPDF;
  y: number;
  page: number;
}

function newPage(layout: Layout): void {
  layout.doc.addPage();
  layout.page += 1;
  layout.y = MARGIN;
}

// Reserve vertical space, breaking to a new page when the block will not fit.
function need(layout: Layout, height: number): void {
  if (layout.y + height > BOTTOM) newPage(layout);
}

function paragraph(
  layout: Layout,
  text: string,
  options: { size?: number; gray?: number; bold?: boolean; gap?: number } = {},
): void {
  const { doc } = layout;
  const size = options.size ?? 10;
  const leading = size * 1.45;

  doc.setFont("helvetica", options.bold ? "bold" : "normal");
  doc.setFontSize(size);
  doc.setTextColor(options.gray ?? INK);

  const lines: string[] = doc.splitTextToSize(text, CONTENT_WIDTH);
  for (const line of lines) {
    need(layout, leading);
    doc.text(line, MARGIN, layout.y);
    layout.y += leading;
  }
  layout.y += options.gap ?? 0;
}

function heading(layout: Layout, text: string): void {
  const { doc } = layout;
  need(layout, 34);
  layout.y += 10;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(INK);
  doc.text(text.toUpperCase(), MARGIN, layout.y, { charSpace: 0.8 });
  layout.y += 6;

  doc.setDrawColor(RULE);
  doc.setLineWidth(0.6);
  doc.line(MARGIN, layout.y, PAGE_WIDTH - MARGIN, layout.y);
  layout.y += 14;
}

// Label and value on one line, with the label in a fixed column so rows align.
function field(layout: Layout, label: string, value: string): void {
  const { doc } = layout;
  const column = 130;
  const leading = 14;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);

  const lines: string[] = doc.splitTextToSize(value, CONTENT_WIDTH - column);
  need(layout, leading * lines.length);

  doc.setTextColor(MUTED);
  doc.text(label, MARGIN, layout.y);
  doc.setTextColor(INK);

  for (const line of lines) {
    doc.text(line, MARGIN + column, layout.y);
    layout.y += leading;
  }
}

function titleBlock(layout: Layout, report: CaseReport): void {
  const { doc } = layout;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.setTextColor(INK);
  doc.text("Myomatlas", MARGIN, layout.y + 8);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(MUTED);
  doc.text(
    "Decision support for abnormal uterine bleeding",
    MARGIN,
    layout.y + 24,
  );

  layout.y += 42;
  doc.setDrawColor(INK);
  doc.setLineWidth(1);
  doc.line(MARGIN, layout.y, PAGE_WIDTH - MARGIN, layout.y);
  layout.y += 20;

  field(layout, "Case", report.caseId);
  field(layout, "Modality", report.modality);
  field(layout, "Generated", new Date().toLocaleString());
}

function myomaBlock(layout: Layout, myoma: MyomaDetail, index: number): void {
  const { doc } = layout;
  const m = myoma.measurement;

  // Keep the finding's title with at least its first lines rather than orphaning it.
  need(layout, 70);
  if (index > 0) layout.y += 6;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(INK);
  doc.text(`${myoma.label}, FIGO type ${myoma.figoType}`, MARGIN, layout.y);
  layout.y += 14;

  const contact =
    [m.contactsCavity && "cavity", m.contactsSerosa && "serosa"]
      .filter(Boolean)
      .join(", ") || "none";

  const facts = [
    myoma.figoTypeName,
    `Group: ${myoma.figoGroup}`,
    `Confidence: ${myoma.confidence}${myoma.provisional ? " (provisional)" : ""}`,
    `Relevance: ${myoma.relevance}`,
  ].join("   |   ");

  paragraph(layout, facts, { size: 9, gray: MUTED });

  const measures =
    `Volume ${m.volumeMl.toFixed(2)} mL   |   ` +
    `Max diameter ${m.maxDiameterMm.toFixed(1)} mm   |   ` +
    `Intramural ${m.intramuralPct.toFixed(0)} percent   |   ` +
    `Contact: ${contact}`;
  paragraph(layout, measures, { size: 9, gray: MUTED, gap: 4 });

  paragraph(layout, myoma.justification, { size: 10 });

  if (myoma.management.length > 0) {
    layout.y += 2;
    // Keep the label with at least its first option instead of stranding it on a page end.
    need(layout, 34);
    paragraph(layout, "Management options", { size: 9, bold: true, gray: MUTED });
    for (const option of myoma.management) {
      const lines: string[] = doc.splitTextToSize(option, CONTENT_WIDTH - 14);
      need(layout, 14 * lines.length);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      doc.setTextColor(INK);
      doc.text("-", MARGIN, layout.y);
      for (const line of lines) {
        doc.text(line, MARGIN + 14, layout.y);
        layout.y += 14;
      }
    }
  }
  layout.y += 6;
}

function footers(doc: jsPDF, total: number): void {
  for (let page = 1; page <= total; page++) {
    doc.setPage(page);
    doc.setDrawColor(RULE);
    doc.setLineWidth(0.6);
    doc.line(MARGIN, PAGE_HEIGHT - MARGIN - 10, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN - 10);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(MUTED);
    doc.text("Myomatlas", MARGIN, PAGE_HEIGHT - MARGIN + 2);
    doc.text(`Page ${page} of ${total}`, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN + 2, {
      align: "right",
    });
  }
}

export function buildCaseReportPdf(
  report: CaseReport,
  myomas: MyomaDetail[],
  intake: ClinicalIntake,
): jsPDF {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const layout: Layout = { doc, y: MARGIN, page: 1 };

  titleBlock(layout, report);

  if (isIntakeProvided(intake)) {
    heading(layout, "Patient context");
    if (intake.age !== null) field(layout, "Age", String(intake.age));
    if (intake.menopausalStatus)
      field(layout, "Menopausal status", MENOPAUSAL_LABEL[intake.menopausalStatus]);
    if (intake.bleedingSeverity)
      field(layout, "Bleeding severity", BLEEDING_LABEL[intake.bleedingSeverity]);
    if (intake.fertilityDesire)
      field(layout, "Fertility desire", FERTILITY_LABEL[intake.fertilityDesire]);
    if (intake.riskFactors.length > 0)
      field(layout, "Risk factors", intake.riskFactors.join(", "));
    if (intake.notes.trim()) field(layout, "Notes", intake.notes.trim());
  } else {
    heading(layout, "Patient context");
    paragraph(layout, "No clinical context was provided for this analysis.", {
      gray: MUTED,
    });
  }

  heading(layout, "Summary");
  paragraph(layout, report.summary);

  heading(layout, "Malignancy assessment");
  paragraph(layout, report.malignancyFlag ? "Flagged for exclusion" : "Not flagged", {
    bold: true,
  });
  paragraph(layout, report.malignancyReason);

  heading(layout, `Findings (${myomas.length})`);
  myomas.forEach((myoma, index) => myomaBlock(layout, myoma, index));

  heading(layout, "Patient explanation");
  paragraph(layout, report.patientExplanation);

  heading(layout, "Important");
  paragraph(layout, DISCLAIMER, { bold: true });

  footers(doc, doc.getNumberOfPages());
  return doc;
}

export function downloadCaseReportPdf(
  report: CaseReport,
  myomas: MyomaDetail[],
  intake: ClinicalIntake,
): void {
  const doc = buildCaseReportPdf(report, myomas, intake);
  doc.save(`Myomatlas_${report.caseId}.pdf`);
}
