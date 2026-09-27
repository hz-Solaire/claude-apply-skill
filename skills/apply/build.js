// Builds an A4 CV PDF from a cv.json (see the shape in agents/apply-cv.md). Empty sections are skipped.
//   node build.js cv.json out.pdf [max_pages]
// Exports through Microsoft Word (Windows). With max_pages, exit code 1 when the PDF runs longer, and it
// prints "~N line(s) free" or "over by ~N line(s)" so the writer can cut precisely. Without it, no limit.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { Document, Packer, Paragraph, TextRun, AlignmentType, BorderStyle, LevelFormat,
  TabStopType } = require('docx');

const [, , inJson, outPdf, maxArg] = process.argv;
if (!inJson || !outPdf) { console.error('usage: node build.js cv.json out.pdf [max_pages]'); process.exit(2); }
const maxPages = maxArg ? Number(maxArg) : null;
const cv = { contact: [], skills: [], experience: [], volunteering: [], projects: [], education: [],
  achievements: [], certifications: [], ...JSON.parse(fs.readFileSync(inJson, 'utf8')) };

const PAGE_LINES = 50; // lines of body text an A4 page holds with this layout (measured)
const FONT = 'Calibri';
const ACCENT = '1F3A5F';
const run = (text, o = {}) => new TextRun({ text, font: FONT, size: 21, ...o });

function heading(text) {
  return new Paragraph({
    spacing: { before: 100, after: 60 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 2 } },
    children: [run(text.toUpperCase(), { bold: true, size: 23, color: ACCENT, characterSpacing: 20 })],
  });
}
const bullet = (text) => new Paragraph({ numbering: { reference: 'b', level: 0 }, spacing: { after: 20 }, children: [run(text)] });
// Left text + right-aligned text on one line (A4 text width = 11906 - 2*1080 = 9746 DXA)
const leftRight = (left, right) => new Paragraph({
  tabStops: [{ type: TabStopType.RIGHT, position: 10106 }],
  spacing: { before: 120, after: 20 },
  children: [...left, run('\t' + (right || ''), { color: '555555' })],
});

const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
    children: [run(cv.name, { bold: true, size: 44, color: ACCENT })] }),
];
if (cv.headline) body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
  children: [run(cv.headline, { size: 24, color: '444444' })] }));
if (cv.contact.length) body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [run(cv.contact.slice(0, 3).join('  |  '), { size: 19, color: '555555' }),
    run(cv.contact.slice(3).join('  |  '), { size: 19, color: '555555', break: 1 })] }));

const role = e => [run(e.role, { bold: true }), run(e.company ? ', ' + e.company : ''),
  run(e.location ? ' · ' + e.location : '', { italics: true, color: '555555', size: 19 })];
const sections = {
  summary: () => cv.summary && [heading('Summary'), new Paragraph({ spacing: { after: 60 }, children: [run(cv.summary)] })],
  education: () => cv.education.length && [heading('Education'), ...cv.education.flatMap(e => [
    leftRight([run(e.degree, { bold: true })], e.dates),
    ...(e.school ? [new Paragraph({ spacing: { after: 40 }, children: [run(e.school, { italics: true, color: '555555', size: 19 })] })] : []),
    ...(e.note ? [new Paragraph({ children: [run(e.note, { color: '555555' })] })] : [])])],
  experience: () => cv.experience.length && [heading('Professional Experience'), ...cv.experience.flatMap(e => [
    leftRight(role(e), e.dates),
    ...(e.blurb ? [new Paragraph({ spacing: { after: 40 }, children: [run(e.blurb, { italics: true, color: '555555', size: 19 })] })] : []),
    ...e.bullets.map(bullet)])],
  projects: () => cv.projects.length && [heading('Projects'), ...cv.projects.flatMap(p => [
    leftRight([run(p.title, { bold: true }), run(p.sub ? ' · ' + p.sub : '', { italics: true, color: '555555', size: 19 })], p.dates),
    ...p.bullets.map(bullet)])],
  volunteering: () => cv.volunteering.length && [heading('Leadership & Volunteering'), ...cv.volunteering.flatMap(e => [
    leftRight(role(e), e.dates), ...e.bullets.map(bullet)])],
  achievements: () => cv.achievements.length && [heading('Achievements'), ...cv.achievements.map(bullet)],
  skills: () => cv.skills.length && [heading('Skills'), ...cv.skills.map(s => new Paragraph({ spacing: { after: 40 },
    children: [run(s.label + ': ', { bold: true }), run(s.items)] }))],
  certifications: () => cv.certifications.length && [heading('Certifications'), ...cv.certifications.map(bullet)],
};
// cv.order picks the section order; anything left out is appended in the default order
const DEFAULT_ORDER = ['summary', 'experience', 'projects', 'education', 'volunteering', 'achievements', 'skills', 'certifications'];
const order = [...new Set([...(cv.order || []), ...DEFAULT_ORDER])].filter(k => sections[k]);
order.forEach(k => body.push(...(sections[k]() || [])));

const doc = new Document({
  numbering: { config: [{ reference: 'b', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•',
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 },
    margin: { top: 540, bottom: 480, left: 900, right: 900 } } }, children: body }],
});

Packer.toBuffer(doc).then(buf => {
  const pdf = path.resolve(outPdf), docx = path.join(os.tmpdir(), `cv-${process.pid}.docx`);
  fs.writeFileSync(docx, buf);
  fs.mkdirSync(path.dirname(pdf), { recursive: true });
  const q = s => s.replace(/'/g, "''");
  let out;
  try {
    // prints page count, then the line number of the document's last line on its page (10 = wdFirstCharacterLineNumber)
    out = execFileSync('powershell', ['-NoProfile', '-Command',
      `$w=New-Object -ComObject Word.Application; $w.Visible=$false; try { $d=$w.Documents.Open('${q(docx)}',$false,$true); ` +
      `$d.ComputeStatistics(2); $d.Range($d.Content.End-1,$d.Content.End).Information(10); ` +
      `$d.ExportAsFixedFormat('${q(pdf)}',17) } finally { if ($d) { $d.Close($false) }; $w.Quit() }`],
      { encoding: 'utf8' }).trim();
  } finally { fs.unlinkSync(docx); }
  if (!fs.existsSync(pdf)) throw new Error(`Word reported success but ${pdf} doesn't exist`);
  const [pages, last] = out.split(/\s+/).map(Number);
  if (!maxPages) return console.log(`wrote ${pdf} (${pages} page(s), no page limit)`);
  const spare = (maxPages - pages) * PAGE_LINES + (PAGE_LINES - last); // negative = overflow
  console.log(spare >= 0 ? `wrote ${pdf} (${pages}/${maxPages} page(s), ~${spare} line(s) free)`
    : `wrote ${pdf} (${pages} pages, limit ${maxPages}: over by ~${-spare} line(s), cut that much)`);
  if (spare < 0) process.exitCode = 1;
});
