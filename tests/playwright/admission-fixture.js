// Synthetic reviewers confirm metadata-only work samples in the isolated API.
async function admitProfessional(api, id) {
  const path = '/api/professionals/' + encodeURIComponent(id);
  async function send(actor, role, endpoint, method, body) {
    const result = await api(actor, role, path + endpoint, { method, body: JSON.stringify(body) });
    if (result.status >= 300) throw new Error(endpoint + ' returned ' + result.status);
    return result.body;
  }
  await send(id, 'professional', '/application', 'POST', {});
  const profile = await send(id, 'professional', '/profile', 'PUT', {
    display_name: 'Synthetic delivery specialist', skills: ['Delivery'],
    evidence_references: [{ label: 'Work sample', reference: 'private://synthetic/sample' }],
  });
  await send('reviewer-1', 'reviewer', '/review', 'POST', {status: 'under_review'});
  await send('reviewer-1', 'reviewer', '/review', 'POST', {
    status: 'approved', reason: 'Reviewed synthetic work sample', reviewed_profile_version: profile.version,
  });
}
module.exports = { admitProfessional };
