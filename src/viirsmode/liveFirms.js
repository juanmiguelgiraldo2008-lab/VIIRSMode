export async function fetchLiveFires(
  fetchImpl = (...args) => globalThis.fetch(...args),
) {
  const response = await fetchImpl('/api/firms', {
    cache: 'no-store',
  });
  const payload = await response.json().catch(() => ({}));
  if (response.status === 503 && payload.error === 'no_key') {
    return { keyRequired: true };
  }
  if (!response.ok) {
    throw new Error(
      payload.error || `NASA FIRMS request failed (${response.status})`,
    );
  }
  if (!Array.isArray(payload.fires)) {
    throw new Error('NASA FIRMS returned an invalid fire snapshot');
  }
  return {
    ...payload,
    fires: payload.fires.map((fire) => ({
      ...fire,
      date: fire.acqDate,
      sensor: fire.instrument,
      weight: 1,
    })),
  };
}
