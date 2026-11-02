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

// Older rows can hold a free-text unit ("hrs", "Pieces", "2") from before this
// list existed. Edit forms show such a value as its own option so the vendor
// sees what is stored instead of a blank "Unit (optional)"; the server maps
// known spellings and leaves an unmappable one untouched.
export const isKnownUnit = (value) => PACKAGE_UNIT_OPTIONS.some((u) => u.value === value);
