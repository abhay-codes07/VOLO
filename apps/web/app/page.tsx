import { TopNav } from "@/components/TopNav";
import { StatusStrip } from "@/components/StatusStrip";
import { Hero } from "@/components/Hero";
import { ProviderStrip } from "@/components/ProviderStrip";
import { RepeatedHeadline } from "@/components/RepeatedHeadline";
import { BentoGrid } from "@/components/BentoGrid";
import { ActivityThread } from "@/components/ActivityThread";
import { NotesGrid } from "@/components/NotesGrid";
import { Testimonials } from "@/components/Testimonials";
import { CTA } from "@/components/CTA";
import { Footer } from "@/components/Footer";
import {
  computeDiff,
  getNamedDiff,
  getRecording,
  getReport,
  listRecordings,
  listReports,
  safe,
} from "@/lib/api";

const BASELINE_STEM = "calc_v1";
const CANDIDATE_STEM = "calc_v2";
const DIFF_STEM = "v1_vs_v2";

export default async function Page() {
  const [recordings, reports] = await Promise.all([
    safe(listRecordings()),
    safe(listReports()),
  ]);

  const baselineRec =
    (await safe(getRecording(BASELINE_STEM))) ??
    (recordings?.[0] ? await safe(getRecording(recordings[0].stem)) : null);
  const candidateRec =
    (await safe(getRecording(CANDIDATE_STEM))) ??
    (recordings?.[1] ? await safe(getRecording(recordings[1].stem)) : null);

  const candidateReport =
    (await safe(getReport(CANDIDATE_STEM))) ??
    (reports?.[1] ? await safe(getReport(reports[1].stem)) : null);

  const diff =
    (await safe(getNamedDiff(DIFF_STEM))) ??
    (baselineRec && candidateRec
      ? await safe(computeDiff(baselineRec.run_id, candidateRec.run_id))
      : null);

  const baselineSummary = reports?.find((r) => r.stem === BASELINE_STEM) ?? reports?.[0] ?? null;
  const candidateSummary = reports?.find((r) => r.stem === CANDIDATE_STEM) ?? reports?.[1] ?? null;
  const failureIndex = diff?.first_diverging_step ?? null;

  return (
    <>
      <StatusStrip
        recordings={recordings?.length ?? 0}
        verdict={candidateSummary?.verdict ?? null}
      />
      <TopNav />

      <Hero
        baselineRec={baselineRec}
        candidateRec={candidateRec}
        baselineSummary={baselineSummary}
        candidateSummary={candidateSummary}
        failureIndex={failureIndex}
      />

      <ProviderStrip />

      <RepeatedHeadline />

      <BentoGrid report={candidateReport} />

      <ActivityThread />

      <NotesGrid />

      <Testimonials />

      <CTA />

      <Footer />
    </>
  );
}
