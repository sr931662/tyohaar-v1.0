import { setSizeOf } from '../constants/packageUnits';

const rupees = (value) => `₹${Number(value).toLocaleString('en-IN')}`;

/**
 * Sits under the Qty / Unit row of every item and service form. Asks for the
 * set size when the unit is "sets", and spells out what the customer will pay
 * so a set size typed into Qty is visible before saving.
 */
export default function SetSizeFields({ form, set }) {
  const isSets = form.unit === 'sets';
  const quantity = Number(form.quantity) || 0;
  const price = Number(form.base_price) || 0;
  const showTotal = price > 0 && quantity > 0 && (isSets || quantity > 1);
  const size = setSizeOf(form);

  if (!isSets && !showTotal) return null;

  const counted = isSets
    ? `${quantity} ${quantity === 1 ? 'set' : 'sets'}${size ? ` of ${size} pieces` : ''}`
    : `${quantity} ${form.unit || 'units'}`;

  return (
    <div>
      {isSets && (
        <input
          className="admin-input"
          type="number"
          min="1"
          value={form.pieces_per_set ?? ''}
          onChange={(e) => set('pieces_per_set', e.target.value)}
          placeholder="Pieces in one set, e.g. 200"
        />
      )}
      <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--text-tertiary)' }}>
        {isSets && 'Qty is the number of sets and the price is for one whole set. '}
        {showTotal && (
          <strong>
            Customer pays for {counted}: {quantity} × {rupees(price)} = {rupees(quantity * price)}
          </strong>
        )}
      </p>
    </div>
  );
}
