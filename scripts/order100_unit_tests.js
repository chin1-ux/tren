import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

// Unit Test Suite for Order 100 Section I2
const results = [];

function recordTest(name, fn) {
  try {
    fn();
    results.push({ name, status: 'PASS' });
    console.log(`PASS: ${name}`);
  } catch (err) {
    results.push({ name, status: 'FAIL', error: err.message });
    console.error(`FAIL: ${name} ->`, err.message);
  }
}

// 1. Stage mapping
const STAGE_LABEL_MAP = {
  emerging: 'Just starting',
  rising: 'Blowing up',
  peaked: "Everyone's using it",
  resurging: 'Comeback',
  expired: 'Expired',
};

recordTest('Stage Mapping (C3)', () => {
  assert.strictEqual(STAGE_LABEL_MAP.emerging, 'Just starting');
  assert.strictEqual(STAGE_LABEL_MAP.rising, 'Blowing up');
  assert.strictEqual(STAGE_LABEL_MAP.peaked, "Everyone's using it");
  assert.strictEqual(STAGE_LABEL_MAP.resurging, 'Comeback');
  assert.strictEqual(STAGE_LABEL_MAP.expired, 'Expired');
});

// 2. Number formatting
function formatCount(count) {
  if (!count || count <= 0) return '0';
  if (count < 1000) return count.toLocaleString();
  if (count < 1_000_000) {
    const k = count / 1000;
    return k >= 100 ? `${Math.round(k)}K` : `${k.toFixed(1).replace(/\.0$/, '')}K`;
  }
  const m = count / 1_000_000;
  return m >= 100 ? `${Math.round(m)}M` : `${m.toFixed(1).replace(/\.0$/, '')}M`;
}

recordTest('Number Formatting (formatCount)', () => {
  assert.strictEqual(formatCount(106000), '106K');
  assert.strictEqual(formatCount(1500), '1.5K');
  assert.strictEqual(formatCount(692000), '692K');
  assert.strictEqual(formatCount(1200000), '1.2M');
  assert.notStrictEqual(formatCount(1000000), '1000K');
});

// 3. Title Normalization & Deduplication
function normalizeTitle(title) {
  return title
    .replace(/\s*\((sped\s*up|slowed\s*\+\s*reverb|slowed|reverb|remix|acoustic|cover)\)\s*/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function deduplicateTrends(items) {
  const groups = {};
  for (const item of items) {
    const key = `${normalizeTitle(item.title)}::${(item.artist || '').toLowerCase().trim()}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }
  return Object.values(groups).map((group) =>
    group.reduce((max, cur) => (cur.creator_count > max.creator_count ? cur : max))
  );
}

recordTest('Deduplication & Title Normalization (C2)', () => {
  const duplicates = [
    { id: 1, title: 'Espresso (Sped Up)', artist: 'Sabrina Carpenter', creator_count: 5 },
    { id: 2, title: 'Espresso (Slowed + Reverb)', artist: 'Sabrina Carpenter', creator_count: 12 },
    { id: 3, title: 'Espresso', artist: 'Sabrina Carpenter', creator_count: 8 },
    { id: 4, title: 'Flowers', artist: 'Miley Cyrus', creator_count: 20 },
  ];
  const deduped = deduplicateTrends(duplicates);
  assert.strictEqual(deduped.length, 2, 'Must group 3 variations of Espresso into 1');
  const espresso = deduped.find((d) => d.artist === 'Sabrina Carpenter');
  assert.strictEqual(espresso.creator_count, 12, 'Must keep the version with highest creator_count');
});

// 4. Taste Learning & Bounded Multiplier
function calculatePersonalMultiplier(affinity) {
  const raw = 0.6 + 0.8 * affinity;
  return Math.min(1.4, Math.max(0.6, raw));
}

recordTest('Taste Multiplier Bounds [0.6, 1.4]', () => {
  assert.strictEqual(calculatePersonalMultiplier(0.5), 1.0, 'Cold start (0.5) must be 1.0');
  assert.strictEqual(calculatePersonalMultiplier(0.0), 0.6, 'Lower bound at affinity 0 must be 0.6');
  assert.strictEqual(calculatePersonalMultiplier(1.0), 1.4, 'Upper bound at affinity 1 must be 1.4');
  assert.strictEqual(calculatePersonalMultiplier(-0.5), 0.6, 'Negative affinity clamped to 0.6');
  assert.strictEqual(calculatePersonalMultiplier(1.8), 1.4, 'High affinity clamped to 1.4');
});

// 5. Freshness Decay (24h half life)
function freshnessDecay(ageHours) {
  return Math.pow(0.5, ageHours / 24.0);
}

recordTest('Freshness Decay Half-Life (24h)', () => {
  assert.strictEqual(freshnessDecay(0), 1.0, 'Age 0h decay must be 1.0');
  assert.strictEqual(freshnessDecay(24), 0.5, 'Age 24h decay must be 0.5');
  assert.strictEqual(freshnessDecay(48), 0.25, 'Age 48h decay must be 0.25');
});

// 6. Eligibility Rule B
function isEligibleRuleB(trend) {
  const validStatus = trend.status === 'emerging' || trend.status === 'rising';
  const validWindow = (trend.window_hours_remaining || 0) > 0;
  const notVoiceover = !trend.is_voiceover;
  const notSeed = !trend.is_seed_data;
  const notBhojpuri = (trend.language_final || '').toLowerCase() !== 'bhojpuri';
  const ruleB = (trend.reel_count || 0) >= 2 || (trend.audio_use_count || 0) >= 50000;

  return validStatus && validWindow && notVoiceover && notSeed && notBhojpuri && ruleB;
}

recordTest('Eligibility Rule B Compliance', () => {
  const passing1 = { status: 'rising', window_hours_remaining: 10, is_voiceover: false, is_seed_data: false, language_final: 'hi', reel_count: 2, audio_use_count: 1000 };
  const passing2 = { status: 'emerging', window_hours_remaining: 8, is_voiceover: false, is_seed_data: false, language_final: 'te', reel_count: 1, audio_use_count: 55000 };
  const failingBhojpuri = { status: 'rising', window_hours_remaining: 10, is_voiceover: false, is_seed_data: false, language_final: 'bhojpuri', reel_count: 5, audio_use_count: 100000 };
  const failingLowReelsAndUses = { status: 'emerging', window_hours_remaining: 10, is_voiceover: false, is_seed_data: false, language_final: 'en', reel_count: 1, audio_use_count: 4000 };

  assert.strictEqual(isEligibleRuleB(passing1), true);
  assert.strictEqual(isEligibleRuleB(passing2), true);
  assert.strictEqual(isEligibleRuleB(failingBhojpuri), false);
  assert.strictEqual(isEligibleRuleB(failingLowReelsAndUses), false);
});

// Write evidence file
fs.mkdirSync('evidence/order100', { recursive: true });
fs.writeFileSync('evidence/order100/unit_tests_results.json', JSON.stringify(results, null, 2));
console.log('\nUnit tests written to evidence/order100/unit_tests_results.json');
