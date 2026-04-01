const AC_API_URL = process.env.ACTIVECAMPAIGN_API_URL;
const AC_API_KEY = process.env.ACTIVECAMPAIGN_API_KEY;

async function acFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  if (!AC_API_URL || !AC_API_KEY) {
    throw new Error('ActiveCampaign env vars not configured');
  }
  const url = `${AC_API_URL}/api/3/${endpoint}`;
  return fetch(url, {
    ...options,
    headers: {
      'Api-Token': AC_API_KEY,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
}

export async function createOrUpdateContact(email: string): Promise<number> {
  const res = await acFetch('contact/sync', {
    method: 'POST',
    body: JSON.stringify({ contact: { email } }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`AC contact sync failed: ${res.status} ${body}`);
  }
  const data = await res.json();
  return Number(data.contact.id);
}

async function findOrCreateTag(tagName: string): Promise<number> {
  // Search for existing tag
  const searchRes = await acFetch(`tags?search=${encodeURIComponent(tagName)}`);
  if (searchRes.ok) {
    const searchData = await searchRes.json();
    const existing = searchData.tags?.find(
      (t: { tag: string }) => t.tag.toLowerCase() === tagName.toLowerCase()
    );
    if (existing) return Number(existing.id);
  }

  // Create new tag
  const createRes = await acFetch('tags', {
    method: 'POST',
    body: JSON.stringify({
      tag: { tag: tagName, tagType: 'contact', description: '' },
    }),
  });
  if (!createRes.ok) {
    const body = await createRes.text();
    throw new Error(`AC tag create failed: ${createRes.status} ${body}`);
  }
  const createData = await createRes.json();
  return Number(createData.tag.id);
}

export async function addTagToContact(contactId: number, tagName: string): Promise<void> {
  const tagId = await findOrCreateTag(tagName);
  const res = await acFetch('contactTags', {
    method: 'POST',
    body: JSON.stringify({
      contactTag: { contact: contactId, tag: tagId },
    }),
  });
  // 422 means tag already assigned — that's fine
  if (!res.ok && res.status !== 422) {
    const body = await res.text();
    console.error(`AC tag assign failed: ${res.status} ${body}`);
  }
}

export async function tagContactFromSurvey(
  contactId: number,
  data: { businessSize: string; sitesManaged: string; useCases: string[] }
): Promise<void> {
  const tags: string[] = [];

  if (data.businessSize) tags.push(`biz-${data.businessSize}`);
  if (data.sitesManaged) {
    const siteTag = data.sitesManaged === '20+' ? 'sites-20-plus' : `sites-${data.sitesManaged}`;
    tags.push(siteTag);
  }
  for (const uc of data.useCases) {
    tags.push(`wants-${uc}`);
  }
  tags.push('onboarding-complete');

  // Apply tags sequentially to respect AC rate limits (5 req/s)
  for (const tag of tags) {
    await addTagToContact(contactId, tag);
  }
}
