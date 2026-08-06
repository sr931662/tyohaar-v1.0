import { toast } from 'sonner';

/**
 * Generalizes PackagesPage's reportBulkResult partial-failure toast logic
 * so every page wired to a BulkOperationResult-shaped mutation gets the
 * same succeeded/failed branching for free.
 *
 * @param {object} params
 * @param {object} params.result - BulkOperationResult: { total_requested, succeeded, failed }
 * @param {string} params.verbPast - e.g. "deleted", "deactivated"
 * @param {string} params.verbIng - e.g. "delete", "deactivate"
 * @param {string} params.nounSingular - e.g. "occasion"
 * @param {string} params.nounPlural - e.g. "occasions"
 * @param {() => void} [params.onDone] - called after the toast fires (e.g. invalidateQueries + clear selection)
 */
export function reportBulkResult({ result, verbPast, verbIng, nounSingular, nounPlural, onDone }) {
  const noun = result.total_requested === 1 ? nounSingular : nounPlural;

  if (result.failed > 0 && result.succeeded === 0) {
    toast.error(`Failed to ${verbIng} ${result.failed === 1 ? `the ${nounSingular}` : `${result.failed} ${nounPlural}`}.`);
  } else if (result.failed > 0) {
    toast.warning(`${result.succeeded} ${noun} ${verbPast}, ${result.failed} failed.`);
  } else {
    toast.success(`${result.total_requested === 1 ? nounSingular : nounPlural} ${verbPast}.`);
  }

  onDone?.();
}
