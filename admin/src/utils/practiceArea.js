// Fixed practice-area enum — mirrors shared/models/enums.py's PracticeArea.
// Shared between CasesListPage (filter + badges) and CaseDetailPage (editor).
export const PRACTICE_AREAS = [
  'traffic',
  'criminal',
  'family',
  'civil',
  'labor',
  'real_estate',
  'corporate',
  'immigration',
]

const LABELS = {
  traffic: 'תעבורה',
  criminal: 'פלילי',
  family: 'משפחה',
  civil: 'אזרחי',
  labor: 'עבודה',
  real_estate: 'מקרקעין',
  corporate: 'מסחרי',
  immigration: 'הגירה',
}

export function practiceAreaLabel(area) {
  return LABELS[area] ?? area
}
