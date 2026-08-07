// Fixed unit catalogue for PackageItem/PackageService quantity units.
//
// Free-text unit entry let admins/vendors type quantities (e.g. '2') into
// the unit field by mistake — this list mirrors the backend's PackageUnit
// enum (server/app/models/enums.py) exactly by value, so every unit picker
// across the admin portal, vendor portal, and customer app stays in sync.
export const PACKAGE_UNIT_OPTIONS = [
  { value: 'pieces', label: 'Pieces' },
  { value: 'sets', label: 'Sets' },
  { value: 'hours', label: 'Hours' },
  { value: 'days', label: 'Days' },
  { value: 'persons', label: 'Persons' },
  { value: 'plates', label: 'Plates' },
  { value: 'sq ft', label: 'Sq. ft.' },
  { value: 'kg', label: 'Kg' },
];
