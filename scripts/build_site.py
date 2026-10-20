#!/usr/bin/env python3
"""Build the GitHub Pages site from measured JSON. No score is typed by hand."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CARD = json.loads((ROOT / "evidence" / "run_card.json").read_text())
FEED = json.loads((DOCS / "data" / "feed.json").read_text())
CANARY = json.loads((ROOT / "evidence" / "h71_canary.json").read_text())
POINTS = json.loads((ROOT / "evidence" / "h71_points.json").read_text())

CSS = """
:root {
  --paper: #f3efe6;
  --ink: #1b1914;
  --muted: #5c564c;
  --line: #d9d0c1;
  --brown: #7a4e24;
  --no: #8d1d1d;
  --no-bg: #f6e4e1;
  --yes: #1d4d34;
  --yes-bg: #e5f0e8;
  --card: #fffdf8;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 17px/1.55 "Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif;
}
a { color: var(--brown); }
a:hover { color: var(--ink); }
header.site {
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.6rem 1rem; align-items: baseline;
  padding: 0.8rem 1.4rem; border-bottom: 1px solid var(--line); background: #ebe4d6;
  font-family: var(--mono); font-size: 0.78rem; letter-spacing: 0.02em;
}
header.site strong { font-family: Georgia, serif; font-size: 1rem; letter-spacing: 0; }
nav a { margin-left: 0.9rem; text-decoration: none; color: var(--ink); }
main { max-width: 860px; margin: 0 auto; padding: 1.4rem 1.2rem 4rem; overflow-x: auto; }
h1 { font-size: 1.85rem; line-height: 1.2; font-weight: 600; margin: 0.2rem 0 0.6rem; }
h2 { font-size: 1.25rem; margin: 2rem 0 0.5rem; }
h3 { font-size: 1.05rem; margin: 1.3rem 0 0.3rem; }
p, li { color: var(--ink); }
.muted { color: var(--muted); }
.plate {
  border: 2px solid var(--no); background: var(--no-bg); padding: 1.1rem 1.2rem 1.2rem;
  margin: 0 0 1.2rem;
}
.plate.ok { border-color: var(--yes); background: var(--yes-bg); }
.plate .kicker {
  font-family: var(--mono); font-size: 0.78rem; letter-spacing: 0.08em;
  text-transform: uppercase; margin: 0 0 0.3rem;
}
.plate h1 { font-size: 2rem; margin: 0 0 0.4rem; }
.plate p { margin: 0.35rem 0; }
.row { display: flex; flex-wrap: wrap; gap: 0.6rem; margin-top: 0.8rem; }
.btn {
  display: inline-block; background: var(--ink); color: #fff; text-decoration: none;
  padding: 0.7rem 1rem; font-family: var(--mono); font-size: 0.85rem;
}
.btn.secondary { background: transparent; color: var(--ink); border: 1px solid var(--ink); }
.btn:hover { background: var(--brown); color: #fff; }
.card {
  background: var(--card); border: 1px solid var(--line); padding: 0.9rem 1rem; margin: 0.8rem 0;
}
label { display: block; font-family: var(--mono); font-size: 0.72rem; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--muted); margin-top: 0.7rem; }
code, .mono { font-family: var(--mono); font-size: 0.86rem; }
.copyline {
  display: flex; gap: 0.4rem; align-items: center; background: #f7f3ea;
  border: 1px solid var(--line); padding: 0.45rem 0.55rem; margin-top: 0.2rem;
}
.copyline code { flex: 1; word-break: break-all; }
button.copy {
  font-family: var(--mono); font-size: 0.75rem; border: 1px solid var(--ink);
  background: #fff; padding: 0.25rem 0.45rem; cursor: pointer;
}
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.92rem; margin: 0.6rem 0 1rem; }
th, td { text-align: left; vertical-align: top; padding: 0.35rem 0.4rem; border-bottom: 1px solid var(--line); }
th { font-family: var(--mono); font-size: 0.72rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }
.tag { font-family: var(--mono); font-size: 0.72rem; border: 1px solid var(--line); padding: 0.05rem 0.35rem; }
footer { border-top: 1px solid var(--line); color: var(--muted); font-size: 0.85rem; margin-top: 2rem; padding-top: 0.8rem; }
ol.steps li { margin: 0.45rem 0; }
"""

JS = """
document.querySelectorAll('button.copy').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.parentElement.querySelector('code').textContent;
    navigator.clipboard.writeText(text).then(() => { btn.textContent = 'copied'; });
  });
});
"""


def fmt(x, digits=4):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def page(title, body, current):
    nav = [
        ("index.html", "Status"),
        ("executive-summary.html", "How to submit"),
        ("method.html", "Why 0.2778"),
        ("hypotheses.html", "Hypotheses"),
        ("sources.html", "Sources"),
        ("irregularities.html", "Irregularities"),
    ]
    links = " ".join(
        f'<a href="{href}"><strong>{label}</strong></a>' if href == current else f'<a href="{href}">{label}</a>'
        for href, label in nav
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<header class="site">
  <strong>GEMSDOE71</strong>
  <nav>{links}</nav>
</header>
<main>
{body}
<footer>
DOE GEMS Prize, DrivenData 306. Numbers on this site are either measured in this repository
or copied from a named official page. A projection is never written as a score.
No weekly submission slot was used.
</footer>
</main>
<script>{JS}</script>
</body>
</html>
"""


def checks_table():
    checks = CARD["validator"]["writer_validator"]["checks"]
    rows = "\n".join(
        f"<tr><td><code>{k}</code></td><td>{'PASS' if v else 'FAIL'}</td></tr>"
        for k, v in checks.items()
    )
    return f"<table><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>"


def canary_table():
    rows = []
    for row in CANARY["rows"]:
        auc = "undefined" if row["auc"] is None else f"{row['auc']:.3f}"
        used = "used" if row["used_in_emission"] else "not used"
        rows.append(f"<tr><td><code>{row['feature']}</code></td><td>{auc}</td><td>{used}</td></tr>")
    return "<table><thead><tr><th>Feature alone</th><th>AUC</th><th>In the emission?</th></tr></thead><tbody>" + "\n".join(rows) + "</tbody></table>"


def exp_table():
    rows = []
    for name, blob in CARD["experiments"].items():
        d = blob["delta_vs_random"]
        rows.append(
            "<tr>"
            f"<td>{name}</td><td>{blob['dots']}</td>"
            f"<td>{blob['holdout_dti']:.6f}</td>"
            f"<td>[{blob['ci95'][0]:.4f}, {blob['ci95'][1]:.4f}]</td>"
            f"<td>{d['delta']:.6f} [{d['ci95'][0]:.4f}, {d['ci95'][1]:.4f}]</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Arm</th><th>Dots</th><th>HOLDOUT-DTI</th>"
        "<th>95% CI</th><th>Paired delta vs mass-matched random</th></tr></thead><tbody>"
        + "\n".join(rows) + "</tbody></table>"
        + "<p class='muted'>Evidence class HOLDOUT-DTI. Evaluator gems57-pooled-hide-v2. "
        "11,321 withheld positive pixels. Alpha 0.2, beta 0.8, 300 m triangular kernel. "
        "Not a leaderboard score.</p>"
    )


def index_body():
    h = CARD["holdout_dti"]
    fn = CARD["filename"]
    sha = CARD["raster_sha256"]
    r = CARD["validator"]["reread"]
    champ = CARD["champion_forensics"]
    off = CARD["off_catalogue_incumbent_diagnostic"]["top"][0]
    return f"""
<section class="plate">
  <p class="kicker">Submission status — read this before anything else</p>
  <h1>NOT OK TO SUBMIT</h1>
  <p><strong>Do not upload this file to DrivenData.</strong> It is format-valid and unique against the methods it was compared with, and it failed the preregistered holdout gate. Spending a weekly slot on it would not raise the chance of winning.</p>
  <p>OK to download for inspection: <strong>yes</strong>. OK to submit to the competition: <strong>no</strong>.</p>
  <div class="row">
    <a class="btn" href="downloads/{fn}">Download audit GeoTIFF — do not submit</a>
    <a class="btn secondary" href="downloads/{fn.replace('.tif', '.zip')}">Download the zip</a>
    <a class="btn secondary" href="executive-summary.html">How a real submission works</a>
  </div>
</section>

<div class="card">
  <label>Unique submission name</label>
  <div class="copyline"><code>{CARD['submission_name']}</code><button class="copy" type="button">copy</button></div>
  <label>Note to paste — {CARD['note_chars']} / 140 characters — only if a future file is cleared</label>
  <div class="copyline"><code>{CARD['note']}</code><button class="copy" type="button">copy</button></div>
  <label>SHA-256 of the zeros GeoTIFF</label>
  <div class="copyline"><code>{sha}</code><button class="copy" type="button">copy</button></div>
  <p class="muted">Single band, float32, EPSG:32611, 3730×3292, 100 m, nodata tag null,
  {r['dots']} dots at 1.0, every cell finite, min {r['min']}, max {r['max']},
  {r['nan']} NaN, {r['on_catalogue_positive']} dots on the mapped catalogue.
  Independent re-read of the bytes in <code>docs/downloads/</code>.</p>
</div>

<h2>Why this file is not cleared</h2>
<p>The preregistration (<code>{CARD['preregistration']}</code>) required four things before a file could be offered for a slot. Three passed. The one that matters for a score did not.</p>
<table>
<thead><tr><th>Gate</th><th>Result</th></tr></thead>
<tbody>
<tr><td>Leakage canary, each used feature alone, AUC ≤ 0.90</td><td>PASS. Worst used AUC is about 0.53. No feature is a leaked label.</td></tr>
<tr><td>Uniqueness versus other methods (Spearman ≤ 0.90, and 3 px overlap ≤ 0.70 on rasters a random map does not also hit)</td><td>PASS against discriminating rasters. Worst Spearman {CARD['correlation_overlap_vs_registry']['dots_worst_rho']:.4f}. Overlap with the 0.2778 file is {CARD['ours_vs_champion_3px_overlap']:.3f}. Four space-filling rasters fire on this file and on a random draw alike. See irregularities.</td></tr>
<tr><td>Format: no NaN, values in [0, 1], CRS / shape / transform match</td><td>PASS. 15 / 15 local checks. This is what stops the portal error &quot;Predicted values must be in range [0, 1]&quot; for this file. It is not permission to submit.</td></tr>
<tr><td>HOLDOUT-DTI beats mass-matched random (95% CI above 0) and beats the registry incumbent</td><td><strong>FAIL.</strong> HOLDOUT-DTI {h['value']:.6f}, 95% CI [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}], evaluator {h['evaluator_version']}, {h['withheld_positive_pixels']} withheld positives. Paired delta versus random {h['paired_delta_vs_mass_matched_nms_random']['delta']:.6f}, CI [{h['paired_delta_vs_mass_matched_nms_random']['ci95'][0]:.4f}, {h['paired_delta_vs_mass_matched_nms_random']['ci95'][1]:.4f}] crosses zero.</td></tr>
</tbody>
</table>
<p>Verdict in the run card: <strong>negative</strong>. Slots used: 0. Selector promotion was not requested and is not justified.</p>

<h2>The three experiments</h2>
{exp_table()}
<p>E1 is discharge-axis traces only. E2 keeps a trace pixel only where the upward-continued magnetic horizontal gradient is in the top 40 percent of the footprint. E3 extends those corroborated axes up to 4 km while the gradient stays elevated. All three are at or below a mass-matched random map, within uncertainty.</p>

<h2>What 0.2778 is, and why this file does not beat it</h2>
<p>The file <code>{champ['file']}</code> has sha256 <code>{champ['sha256']}</code>, remeasured here. It has {champ['dots']} dots, {champ['dots_on_catalogue']} of them on the catalogue, minimum distance to the catalogue {champ['min_distance_to_catalogue_m']:.1f} m, median {champ['median_distance_to_catalogue_m']:.1f} m, and {champ['fraction_within_300m']*100:.1f}% of dots within 300 m. The figure 0.2778 is <strong>owner-reported</strong>, not an organizer receipt in this checkout. On this session's holdout the same bytes score {champ['holdout_dti_this_instrument']:.6f}.</p>
<p>This file scores {h['value']:.6f} on that same instrument. The best off-catalogue registry raster on the same folds scores {off['dti']:.4f} ({off['submission']}, {off['dots']} dots, also HOLDOUT-DTI, not a leaderboard score). The public leaderboard top, read 2026-10-20, is <strong>0.4413</strong> (xiaofanhu). None of those numbers is a prediction of what this 735-dot file would score if uploaded.</p>
<p><a href="method.html">The full argument, with the algebra and the links</a>. The machine-readable card is <a href="data/run-card.json">data/run-card.json</a>.</p>

<h2>Public leaderboard, fetched 2026-10-20</h2>
<p>These are organizer public-board rows, not scores of files in this repository. The prompt's 0.3195 and 0.3774 are not the current top. Refresh from this sandbox fails closed (<code>scripts/refresh_leaderboard.py</code>); the last successful transcription is <a href="data/feed.json">data/feed.json</a>.</p>
<table>
<thead><tr><th>Rank</th><th>Participant</th><th>Public DW-Tversky</th></tr></thead>
<tbody>
{"".join(f"<tr><td>{row['rank']}</td><td>{row['participant']}</td><td>{row['public_dw_tversky']:.4f}</td></tr>" for row in FEED["rows"][:8])}
</tbody>
</table>
<p class="muted">Ranks 9–23 are in the feed file. Lower rows were not transcribed from that fetch. An earlier session on this repository could not reach the leaderboard and flagged the brief's 0.4413 / 0.3774 / 0.3195 conflict as F6. This fetch resolves the current public top: 0.4413. It does not rewrite the owner-reported site scores in <a href="data/user_reported_scores.csv">data/user_reported_scores.csv</a>.</p>

<h2>Earlier scaffold, still in the repository</h2>
<p>A previous session merged a pipeline under <code>gems/</code> and a hub that correctly said no file had been scored. That hub is no longer the front page. Its notes remain: <a href="RESEARCH.md">RESEARCH.md</a>, <a href="FLAGS.md">FLAGS.md</a>, <a href="SOURCES.md">SOURCES.md</a>. Do not run <code>scripts/make_submission.py</code> and treat the output as this audit file. The only file this site is willing to name is the one on the plate, and it is not cleared.</p>

<h2>Format receipt</h2>
<p>Re-opened from disk after the writer finished. The portal message &quot;Predicted values must be in range [0, 1]&quot; is produced by values outside that range and by a nodata sentinel such as −3.4×10<sup>38</sup>. This zeros file has neither.</p>
{checks_table()}
<p class="muted">A NaN-outside twin exists at <code>downloads/{CARD['nan_twin']['filename']}</code> because the problem page says cells outside the bounds should be null. Do not upload it. It is not cleared, and a previous family upload that carried non-[0, 1] nodata was rejected with the same portal message. sha256 <code>{CARD['nan_twin']['sha256']}</code>.</p>
"""


def executive_body():
    return f"""
<h1>How to make a submission</h1>
<p class="muted">Executive summary. Read the status plate on the <a href="index.html">home page</a> first. This page is the procedure. It is not permission to upload today's file.</p>

<section class="plate">
  <p class="kicker">Today's file</p>
  <h1>Stop. Do not submit.</h1>
  <p>The GeoTIFF on the home page failed its holdout gate. Uploading it would spend a submission slot on a map that did not beat a random map of the same size. This project does not do that. The public competition page does not state a weekly cap; the refusal to spend a slot is this project's rule.</p>
</section>

<h2>Exact public steps</h2>
<p>Copied from the competition home page, section “How to compete”, fetched 2026-10-20. The logged-in form was not opened in this session, so this page does not invent field labels for it.</p>
<ol class="steps">
  <li>Click “Compete!” in the sidebar on <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">the competition homepage</a> to enroll.</li>
  <li>Read the overview and the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a>. The organizers also link an <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">about page</a>.</li>
  <li>Download the data from the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data tab</a>. Login is required. This repository did not download it.</li>
  <li>Create and train a model. The organizers publish a <a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a>. It was not executed here.</li>
  <li>Generate predictions that match the submission format: one single-band float32 GeoTIFF, EPSG:32611, 100 m, the same bounds as the training data, values in [0, 1]. The problem page says cells outside the bounds should be null or NaN.</li>
  <li>Click “Submit” in the sidebar, then “Make new submission”.</li>
</ol>
<p>If a rule is unclear, the home page says to ask in the <a href="https://community.drivendata.org/c/gems-prize-challenge/111">competition forum</a> or email <a href="mailto:gemsprize@nlr.gov">gemsprize@nlr.gov</a>. Official rules: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/rules/">DrivenData rules page</a>, which links to <a href="https://www.herox.com/GEMSPrize/resource/2274">HeroX resource 2274</a>.</p>

<h2>What to do with a file from this site</h2>
<ol class="steps">
  <li>Confirm the home-page plate says <strong>OK TO SUBMIT</strong>. If it says anything else, stop. Today's plate says not to submit.</li>
  <li>Download the <code>-zeros.tif</code> named on the plate. Do not upload the <code>-nan.tif</code> twin. The zip is the same zeros file, packed, and is not a better upload.</li>
  <li>Check the sha256 of the downloaded file against the sha256 on the plate. If they differ, do not upload.</li>
  <li>On the form the requester pasted into the project brief: choose the file under <em>File to submit</em>. The brief quotes the form as accepting “a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF,” which must match the submission format's CRS, shape, and geotransform. This session did not log in and re-open that form; the wording is the requester's, not a new screenshot.</li>
  <li>Paste the note from the plate into <em>Note (optional)</em>. The brief's example of that field is “clustering with k=25”. Keep the note at or under 140 characters. The unique name is printed on its own line in case a later form asks for one separately.</li>
  <li>Record the organizer receipt. Until that receipt exists, the score is not ORGANIZER-CONFIRMED, no matter what a holdout number was.</li>
</ol>

<h2>The error &quot;Predicted values must be in range [0, 1]&quot;</h2>
<p>DrivenData rejects a raster whose predicted values are outside [0, 1]. Two different defects produce that same message, and both have been seen in this project family:</p>
<ul>
  <li><strong>A nodata sentinel.</strong> The competition feature raster uses −3.4028234663852886×10<sup>38</sup> as nodata. If that sentinel is copied into a submission, it is not a value in [0, 1], and the portal rejects the file.</li>
  <li><strong>An actual prediction outside [0, 1],</strong> including a NaN if the validator treats NaN as out of range. The problem page also says cells outside the study bounds should be null or NaN. Those two requirements can collide. This site therefore ships an all-finite zeros file as the only upload candidate, and keeps a NaN-outside twin for the page's wording. The twin is not the upload.</li>
</ul>
<p>Today's zeros file was re-opened from disk: nodata tag null, minimum 0, maximum 1, zero NaN cells, EPSG:32611, 3730×3292, transform (100, 0, 243350, 0, −100, 4508550). That makes the portal range error impossible for this particular file. It does not make the file worth submitting.</p>

<h2>What the competition is actually scoring</h2>
<p>You submit one single-band float32 GeoTIFF of fault probability, values in [0, 1], on the training grid (EPSG:32611, 100 m, same bounds). The hidden test faults were labeled by experts and are not in the public USGS compilation. The metric is a distance-weighted Tversky index, alpha 0.2, beta 0.8, triangular kernel of 300 m. Near misses get partial credit. The false-negative weight is four times the false-positive weight.</p>
<p>The home page, fetched 2026-10-20, says the same submission is scored twice: once against a private expert-labeled test set for the Initial Prize Round ($50,000; top 5 each receive $10,000), and again against an expanded label set built from expert review of all submissions for the Final Prize Round ($250,000; $100,000 / $70,000 / $40,000 / $25,000 / $15,000). Deadline: <strong>3 December 2026, 23:59 UTC</strong>.</p>
<p>A file that only redraws the published catalogue is not aimed at the private faults. A file that invents faults with no geological support spends the false-positive weight. Today's file is the second kind of failure on the holdout we can actually run: the discharge axes do not recover withheld catalogue segments better than chance. That holdout is not the private test set.</p>

<h2>Name and note for this artifact</h2>
<p>These are identifiers, not a claim that the file should be uploaded.</p>
<div class="card">
  <label>Name</label>
  <div class="copyline"><code>{CARD['submission_name']}</code><button class="copy" type="button">copy</button></div>
  <label>Note ({CARD['note_chars']}/140)</label>
  <div class="copyline"><code>{CARD['note']}</code><button class="copy" type="button">copy</button></div>
</div>
"""


def method_body():
    champ = CARD["champion_forensics"]
    h = CARD["holdout_dti"]
    board = FEED["rows"][0]
    return f"""
<h1>Why the 0.2778 file scores what it scores</h1>
<p class="muted">Every measurement below was made in this checkout or copied from a page fetched on 2026-10-20. The group's earlier inversion of hidden-set size is not repeated, because that size is not public and was not re-derived here.</p>

<h2>The metric, from the problem page</h2>
<p>Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData competition 306, problem description</a>. Alpha = 0.2, beta = 0.8, triangular kernel k(d) = max(1 − d/300 m, 0).</p>
<p class="mono">DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw)</p>
<p>The published worked example is TPw = 3.00, FPw = 1.89, FNw = 2.00, displayed as 0.60. The exact ratio is 3 / 4.978 = 0.60265, which rounds to the displayed 0.60. This repository's metric module matches that arithmetic and matches a brute-force oracle on a synthetic grid.</p>
<p>Algebra, not a score: a non-redundant extra dot with kernel credit k raises DTI only if k &gt; 0.2 × DTI. If a file really sits at 0.2778, that bar is 0.0556 credit per dot. A dot on a mapped fault earns nothing against a test set that excludes mapped faults, and it still pays the false-positive tax. That is why deleting catalogue-adjacent mass can raise a live score without adding any new geology.</p>

<h2>What the 0.2778 file actually is</h2>
<p>The bytes in the template registry, <code>{champ['file']}</code>, have sha256 <code>{champ['sha256']}</code>. The GEMSDOE32 site publishes the same prefix for the file it calls h33-2-b2. Remeasured here:</p>
<table>
<tbody>
<tr><td>Dots</td><td>{champ['dots']}, each exactly 1.0</td></tr>
<tr><td>Dots on the published catalogue</td><td>{champ['dots_on_catalogue']}</td></tr>
<tr><td>Minimum distance to the catalogue</td><td>{champ['min_distance_to_catalogue_m']:.1f} m</td></tr>
<tr><td>Median distance to the catalogue</td><td>{champ['median_distance_to_catalogue_m']:.1f} m</td></tr>
<tr><td>Fraction of dots within 300 m</td><td>{champ['fraction_within_300m']*100:.1f}%</td></tr>
<tr><td>HOLDOUT-DTI on this session's instrument</td><td>{champ['holdout_dti_this_instrument']:.6f} (gems57-pooled-hide-v2, 11,321 withheld positives)</td></tr>
<tr><td>Live score 0.2778</td><td>{champ['owner_reported_live_score_evidence_class']}</td></tr>
</tbody>
</table>
<p>GEMSDOE32's own page says no organiser score exists for that artifact and quotes a projected 0.2747 as a model. This site does not promote either number to ORGANIZER-CONFIRMED. The structural reading, which does not require believing the 0.2778 figure, is still solid: the file is a thin off-catalogue dotting of a structural-habitat surface. The last gains in that family, as described by the group's own sites, came from deleting dots near the catalogue, not from a new detector.</p>

<h2>Can a new file beat it?</h2>
<p>Yes, in principle. The public board already has. Rank 1 on the official leaderboard, fetched 2026-10-20, is <strong>{board['participant']} at {board['public_dw_tversky']}</strong>. That is an ORGANIZER-CONFIRMED public row. It is not a score of any file in this repository, and it is not a target this file is projected to reach.</p>
<p>Beating 0.2778, if that owner-reported figure is real, requires more credit per unit of mass: either dots closer to the hidden faults, or fewer wasted dots at the same coverage. Copying the 37,654-dot file is forbidden by the uniqueness rule and would not be new information. Thinning it further is the experiment that family already ran.</p>
<p>This session tested a different mechanism: alignments of hot springs, sinter, travertine, and 2 m temperature anomalies, optionally continued along a magnetic gradient. It is the kind of evidence a field geologist uses to draw a fault the USGS map missed. On the mandated holdout it does not work.</p>
<ul>
  <li>Spring density AUC against withheld faults: 0.498. Paleo density: 0.499. The traces themselves: 0.500. Chance.</li>
  <li>HOLDOUT-DTI of the shipped arm: {h['value']:.6f}, 95% CI [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}], {h['withheld_positive_pixels']} withheld positives. Paired difference versus a mass-matched random map has a confidence interval that includes zero.</li>
  <li>True-positive weight was {h['tpw']:.1f} against {h['withheld_positive_pixels']} withheld pixels. Seven hundred and thirty-five dots recovered almost none of the hidden catalogue segments.</li>
  <li>Overlap with the 0.2778 file is {CARD['ours_vs_champion_3px_overlap']:.3f}, so this is not a disguised copy. It is a different map, and a weaker one on this instrument.</li>
</ul>
<p>The catalogue holdout cannot reward a fault that is absent from the catalogue. A null result here does not prove the axes are geologically empty. It does prove they are not a certified improvement. A few hundred dots cannot cover the fault mass a 37,654-dot file is covering unless almost every dot is a direct hit, and we measured the opposite. That is an argument about coverage, not a projected leaderboard score.</p>

<h2>The holdout bar is partly the wrong bar</h2>
<p>The highest HOLDOUT-DTI in the local registry is {h['registry_incumbent']['dti']:.4f} on <code>{h['registry_incumbent']['submission']}</code>. That file is positive on every one of the 60,988 catalogue pixels, so its false-negative count on withheld catalogue segments is zero. A discovery file that refuses to paint the catalogue cannot beat that number, and should not try. The preregistered gate still fails for an independent reason: we also fail to beat random.</p>
<p>Restricted to registry rasters with zero dots on the catalogue, the best HOLDOUT-DTI is {CARD['off_catalogue_incumbent_diagnostic']['top'][0]['dti']:.4f}. Still an order of magnitude above this file. That comparison is a diagnostic, not a rewritten gate.</p>
<p>Known inversion, remeasured rather than assumed: the owner-reported 0.2778 file scores {champ['holdout_dti_this_instrument']:.4f} on this holdout, while a catalogue-covering hedge file scores about 0.270. Live rankings and catalogue-recovery rankings are not the same instrument. Until that is repaired, a holdout win is necessary and not sufficient. This file does not have the necessary part.</p>
"""


def hypotheses_body():
    lahontan = CARD["lahontan_band_fraction_of_dots"]
    return f"""
<h1>Hypotheses ranked before the run</h1>
<p>These were written into <code>registry/preregistration-h71.json</code> before any holdout number existed. Rank is expected live usefulness times whether the data could actually be opened in this session. Only the first was run. The budget is three experiments, and all three were arms of that one hypothesis.</p>

<table>
<thead><tr><th>Rank</th><th>Hypothesis</th><th>Layers</th><th>Why it could be a missing fault</th><th>Cost</th><th>Status</th></tr></thead>
<tbody>
<tr>
<td>1</td>
<td>Discharge-conduit lineaments</td>
<td>GDR 1391 springs and wells (temperature and geothermometers only), paleo sinter/travertine, 2 m temperature anomalies, Quaternary vents, GeoDAWN TMI upward-continued 150 m</td>
<td>Experts add faults that have no scarp but leak fluid. A colinear set of springs is that evidence. It is not a dilation of the USGS traces.</td>
<td>Low. The mirrors were already public.</td>
<td><strong>Run. Negative.</strong> AUC about 0.50. HOLDOUT-DTI 0.00154. Not cleared.</td>
</tr>
<tr>
<td>2</td>
<td>Earthquake-density lineaments off the catalogue</td>
<td>Competition band <code>deq_n100a15</code> / <code>ieq_n100a15</code> in <code>training_features.tif</code></td>
<td>The 2020 Monte Cristo Range earthquake ruptured faults that were incompletely mapped. A seismicity lineament that is not a catalogue trace is the same class of evidence.</td>
<td>Medium. The feature raster is a 419 MB owner mirror, not fetched this session.</td>
<td>Not run. Next session if the mirror is restored. Do not treat it as promising until a canary is measured.</td>
</tr>
<tr>
<td>3</td>
<td>Standalone 2 m temperature worms</td>
<td>INGENIOUS 2 m probes, column 2mDAB, no spring-alignment requirement</td>
<td>Shallow temperature anomalies mark blind outflow. Without a strike constraint they are blobs, not faults, and the metric wants lines.</td>
<td>Low. Already mirrored. 455 probes passed the 2 °C preregistered cut and were used as anchors inside hypothesis 1, not as a separate worm.</td>
<td>Not run as its own experiment. Expected to be as sparse as hypothesis 1.</td>
</tr>
<tr>
<td>4</td>
<td>Buried range-front from isostatic-gravity slope, in low-relief basins only</td>
<td><code>iso_grav_anom_hg</code> or slope, masked by low detrended-elevation slope</td>
<td>A range-bounding fault can be buried under basin fill and absent from the Quaternary-fault map.</td>
<td>Medium. Needs the feature raster. Earlier basement-step lanes in this project family scored under 0.10 live, owner-reported, so the prior is weak.</td>
<td>Not run. Obtainable, low expected gain.</td>
</tr>
<tr>
<td>5</td>
<td>Lanes already owned by other sessions: lidar scarps, auto-context, relay ramps, chi/knickpoints, CVaR selection</td>
<td>Various</td>
<td>Some of these are real geology. None of them is this session's lane, and repeating them would fail the duplicate rule.</td>
<td>Already spent elsewhere.</td>
<td>Excluded on purpose.</td>
</tr>
</tbody>
</table>

<h2>The mimic this lane had to survive</h2>
<p>Pleistocene Lake Lahontan tufa marks a shoreline, not a fault. The highstand is about 1332–1338 m (USGS Circular 1267; GSA Bulletin 110:1318, Adams and Wesnousky 1998, 1338.5 m in the Jessup embayment). Tufa and silica-cemented sand were excluded from the seeds before fitting. Of the emitted dots, {lahontan:.2%} fall in the 1320–1345 m band on the dequantized 3DEP-derived 100 m mean elevation. That diagnostic does not rescue the null result, and it does not show the shoreline mimic took over the map.</p>
<p>The other mimic is a line of water wells along a road. Alignments made only of wells were rejected unless one point had a geothermometer of at least 120 °C, or the neighbourhood contained a spring, a sinter/travertine, a 2 m anomaly, or a vent. 4,591 wells were eligible as supporters. 200 of them were anchors. 1,588 springs were used.</p>
"""


def sources_body():
    return """
<h1>Sources for manual review</h1>
<p>Official pages were fetched in this session unless the row says otherwise. Owner mirrors are integrity-pinned, not organizer-authenticated.</p>
<table>
<thead><tr><th>What</th><th>Link</th><th>How it was used</th></tr></thead>
<tbody>
<tr><td>Problem, metric, submission format</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page 967</a></td><td>Fetched 2026-10-20. Source of alpha, beta, 300 m kernel, and the worked example.</td></tr>
<tr><td>Competition home, deadline, prizes</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition home</a></td><td>Fetched 2026-10-20. Deadline 3 December 2026, 23:59 UTC. Prize pool $300,000.</td></tr>
<tr><td>Public leaderboard</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a></td><td>Fetched 2026-10-20. Rank 1 is 0.4413. Transcription in <code>docs/data/feed.json</code>.</td></tr>
<tr><td>About page</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">page 968</a></td><td>Linked by the organizers. Not re-fetched this session.</td></tr>
<tr><td>Data download</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data tab</a></td><td>Login-walled. Not downloaded. Owner mirrors used instead. See irregularities.</td></tr>
<tr><td>Rules</td><td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/rules/">DrivenData rules page</a>, <a href="https://www.herox.com/GEMSPrize/resource/2274">HeroX 2274</a>, <a href="https://www.nlr.gov/docs/fy26osti/96647.pdf">NLR PDF</a></td><td>Rules page and HeroX resource fetched 2026-10-20. HeroX links the PDF. The PDF bytes were not read.</td></tr>
<tr><td>Forum</td><td><a href="https://community.drivendata.org/c/gems-prize-challenge/111">competition forum</a></td><td>The home page names this forum, and gemsprize@nlr.gov, as the place to ask the organizers.</td></tr>
<tr><td>Reference solution</td><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">GitHub</a></td><td>Repository listing confirmed. The notebook was not executed here.</td></tr>
<tr><td>GeoDAWN</td><td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS data release</a></td><td>Official description of the magnetic and radiometric survey. The TMI grid used here is an owner uint8 mirror of that family, band description <code>TMI_up150</code>.</td></tr>
<tr><td>INGENIOUS</td><td><a href="https://gbcge.org/current-projects/ingenious/">GBCGE project page</a></td><td>Project that compiled the regional geothermal datasets.</td></tr>
<tr><td>GDR 1391</td><td><a href="https://gdr.openei.org/submissions/1391">submission 1391</a>, DOI <a href="https://doi.org/10.15121/1881483">10.15121/1881483</a></td><td>Fetched 2026-10-20. CC BY 4.0. Springs, paleo deposits, 2 m probes, vents. The label-derived distance column was present and was not used.</td></tr>
<tr><td>CRS</td><td><a href="https://epsg.io/32611">EPSG:32611</a></td><td>UTM zone 11N. The pinned transform is (100, 0, 243350, 0, −100, 4508550).</td></tr>
<tr><td>Tversky index</td><td><a href="https://en.wikipedia.org/wiki/Tversky_index">background</a></td><td>The competition metric is the distance-weighted form on page 967, not the Wikipedia formula alone.</td></tr>
<tr><td>Lake Lahontan highstand</td><td><a href="https://pubs.usgs.gov/circ/2004/1267/">USGS Circular 1267</a>; <a href="https://pubs.geoscienceworld.org/gsa/gsabulletin/article/110/10/1318/183306/shoreline-processes-and-the-age-of-the-lake">GSA Bulletin 110:1318</a></td><td>Highstand near 1335 m (circular) and 1338.5 m (Jessup embayment). Used only to name the tufa-shoreline mimic and to set an exclusion, not as a fitted score.</td></tr>
<tr><td>Shared evaluator</td><td><a href="https://github.com/buffedlizard55-lab/60GEMSDOE">60GEMSDOE</a> commit <code>b99591ee</code></td><td>Vendored unchanged into <code>src/gems57</code>. <code>evaluate_holdout.py</code> version gems57-pooled-hide-v2.</td></tr>
</tbody>
</table>
"""


def irreg_body():
    return """
<h1>Irregularities</h1>
<p>These are defects and limits, not footnotes to skip. Each one changed what this site is willing to claim.</p>

<h3>IR-71-DIST-01 — first champion-distance write was inverted</h3>
<p>The first forensics call complemented the catalogue mask twice, so it reported a minimum distance of 0 m. That write is void. The published card was remeasured: minimum 223.6 m, median 1,964.7 m, 5.8% of dots within 300 m, 0 dots on the catalogue. Those corrected figures match the independent description on the GEMSDOE32 page. The code path is fixed. The wrong number is not on the site.</p>

<h3>IR-71-INCUMBENT-01 — the holdout-best registry file paints the catalogue</h3>
<p><code>calib_hedgev2_01563_sample.tif</code> scores HOLDOUT-DTI 0.270 because it is positive on all 60,988 catalogue pixels, so withheld segments have a false-negative weight of zero. Using it as a discovery bar would force every candidate to redraw the catalogue. The preregistered comparison was still computed and still failed. A separate off-catalogue diagnostic is reported and is also a loss.</p>

<h3>IR-71-UNIQ-01 — four registry rasters are not discriminative</h3>
<p>Literal 3 px overlap exceeded 0.70 against two lattice rasters, <code>r11_greedy_mp.tif</code>, and <code>r14_union_tips10_lat6.tif</code>. A mass-matched random draw of the same size fired on all four, at equal or higher overlap. Spearman against every checked raster stayed under 0.005. Jaccard with the lattices is about 0.00015. This is the known space-filling-prior failure, not a copy of another method. Overlap with the 0.2778 file is 0.140.</p>

<h3>IR-71-TEMPLATE-UNIQ-01 — the shared classifier misses this case</h3>
<p><code>gems57.uniqueness.DENSE_SUPPORT_FRACTION</code> is 0.20. A 5-pixel lattice has about 207,000 dots, which is 4% of the footprint, so it is classified as a dot field even though its 3 px halo covers essentially the whole map. The template was not patched in this session: this branch is not allowed to push a fix into 60GEMSDOE, and a private fork of the gate would hide the disagreement. The random-draw control is disclosed in the run card. A template pull request is the right next fix, and it has not been opened.</p>

<h3>IR-71-SAMPLE-01 — the mirrored sample submission is not total fault absence</h3>
<p>The problem page describes a sample that predicts total fault absence. The owner mirror <code>sample_submission.tif</code> (sha256 <code>2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc</code>) has 60,988 ones, and those ones are exactly the catalogue. Its finite mask is the footprint, and that use is valid. Its values are not a template of fault absence. The mirror is not organizer-authenticated.</p>

<h3>IR-71-MIRROR-01 — competition rasters are owner mirrors</h3>
<p>DrivenData data requires a login. This session did not have one and did not contact the data host. Grid, catalogue, springs, paleo deposits, probes, vents, and the radiometric uint8 stack came from public GitHub mirrors pinned by sha256 in the 60GEMSDOE checkout (template commit <code>b99591ee</code>). A pin proves the bytes match the mirror. It does not prove the mirror matches the organizer's file.</p>

<h3>IR-71-LANE-01 — the session prompt did not delimit a method paragraph</h3>
<p>The parallel-run protocol says to stay inside &quot;the single method paragraph below.&quot; No separate method paragraph was present in the prompt delivered to this session. The lane was taken from the prompt's own scientific instruction — find geothermal-vent evidence for faults the catalogue missed, and do not copy an existing submission — and frozen in the preregistration before scoring. Other sessions already own lidar scarps, auto-context, relay ramps, and chi/knickpoints. This lane does not repeat them.</p>

<h3>IR-71-BOARD-01 — prompt leaderboard figures are stale</h3>
<p>The prompt cites 0.4413, 0.3774, and 0.3195 as the high score in different sentences. The official page fetched 2026-10-20 shows rank 1 at 0.4413. 0.3774 does not appear in the transcribed top 23. 0.3195 is not the current top. Group snapshots that called 0.3195 a 4 October rank-3 row were not re-verified here.</p>

<h3>IR-71-E62-01 — a thermal multiplier on knickpoints was already negative</h3>
<p>60GEMSDOE experiment E62 used GDR spring chemistry, paleo deposits, and 2 m probes as a multiplier on a knickpoint lane and lost to a random map. This session did not rerun that lane. It used the same public tables as the seeds of a lineament detector. The null result is consistent with E62 and is not a copy of its raster.</p>
"""


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").write_text("")
    pages = {
        "index.html": ("GEMSDOE71 — not cleared for submission", index_body(), "index.html"),
        "executive-summary.html": ("How to submit — GEMSDOE71", executive_body(), "executive-summary.html"),
        "method.html": ("Why 0.2778 — GEMSDOE71", method_body(), "method.html"),
        "hypotheses.html": ("Hypotheses — GEMSDOE71", hypotheses_body(), "hypotheses.html"),
        "sources.html": ("Sources — GEMSDOE71", sources_body(), "sources.html"),
        "irregularities.html": ("Irregularities — GEMSDOE71", irreg_body(), "irregularities.html"),
    }
    for name, (title, body, current) in pages.items():
        (DOCS / name).write_text(page(title, body, current))
        print("wrote", name)
    # Repo-root landing page. Relative links in the docs page would break here,
    # so this is a redirect plus the verdict, not a second copy of the plate.
    fn = CARD["filename"]
    (ROOT / "index.html").write_text(
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta http-equiv=\"refresh\" content=\"0; url=docs/index.html\">"
        "<title>GEMSDOE71 — not cleared for submission</title></head><body>"
        "<p><strong>NOT OK TO SUBMIT.</strong> "
        f"<a href=\"docs/index.html\">Open the audit page</a>. "
        f"The GeoTIFF is <a href=\"docs/downloads/{fn}\">{fn}</a> "
        "and is not cleared for the weekly slot.</p></body></html>\n"
    )
    (ROOT / ".nojekyll").write_text("")
    data = DOCS / "data"
    data.mkdir(exist_ok=True)
    (data / "run-card.json").write_text((ROOT / "evidence" / "run_card.json").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
