import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi } from '../../api';
import { SkeletonCard } from '../../../admin/components/ui/Skeleton';

const EMPTY_SLOTS = [];

const DAYS = [
  { key: 'monday', label: 'Monday' },
  { key: 'tuesday', label: 'Tuesday' },
  { key: 'wednesday', label: 'Wednesday' },
  { key: 'thursday', label: 'Thursday' },
  { key: 'friday', label: 'Friday' },
  { key: 'saturday', label: 'Saturday' },
  { key: 'sunday', label: 'Sunday' },
];

function defaultDay() {
  return {
    id: null,
    is_working: false,
    open_time: '09:00',
    close_time: '18:00',
    break_start: '',
    break_end: '',
    max_bookings_per_day: 3,
  };
}

function buildScheduleFromSlots(slots) {
  const schedule = {};
  for (const { key } of DAYS) schedule[key] = defaultDay();
  for (const slot of slots) {
    if (!schedule[slot.day_of_week]) continue;
    schedule[slot.day_of_week] = {
      id: slot.id,
      is_working: slot.is_working,
      open_time: (slot.open_time ?? '09:00').slice(0, 5),
      close_time: (slot.close_time ?? '18:00').slice(0, 5),
      break_start: slot.break_start ? slot.break_start.slice(0, 5) : '',
      break_end: slot.break_end ? slot.break_end.slice(0, 5) : '',
      max_bookings_per_day: slot.max_bookings_per_day ?? 3,
    };
  }
  return schedule;
}

function toPayload(day) {
  return {
    is_working: day.is_working,
    open_time: day.is_working && day.open_time ? `${day.open_time}:00` : null,
    close_time: day.is_working && day.close_time ? `${day.close_time}:00` : null,
    break_start: day.is_working && day.break_start ? `${day.break_start}:00` : null,
    break_end: day.is_working && day.break_end ? `${day.break_end}:00` : null,
    max_bookings_per_day: Number(day.max_bookings_per_day) || 1,
  };
}

export default function VendorAvailabilityPage() {
  const qc = useQueryClient();
  const [schedule, setSchedule] = useState(() => buildScheduleFromSlots([]));
  const [saving, setSaving] = useState(false);

  const { data: vendor } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
  });
  const vendorId = vendor?.id;

  const { data, isLoading } = useQuery({
    queryKey: ['vendor-availability', vendorId],
    queryFn: () => vendorProfileApi.listAvailability(vendorId),
    enabled: !!vendorId,
  });
  const slots = data ?? EMPTY_SLOTS;

  useEffect(() => {
    setSchedule(buildScheduleFromSlots(slots));
  }, [slots]);

  const updateDay = (key, patch) => {
    setSchedule((s) => ({ ...s, [key]: { ...s[key], ...patch } }));
  };

  const applyToWeekdays = () => {
    const monday = schedule.monday;
    setSchedule((s) => {
      const next = { ...s };
      for (const day of ['tuesday', 'wednesday', 'thursday', 'friday']) {
        next[day] = { ...next[day], is_working: true, open_time: monday.open_time, close_time: monday.close_time, break_start: monday.break_start, break_end: monday.break_end };
      }
      next.monday = { ...next.monday, is_working: true };
      return next;
    });
    toast.success("Monday's hours applied to Tue–Fri.");
  };

  const validate = () => {
    for (const { key, label } of DAYS) {
      const day = schedule[key];
      if (!day.is_working) continue;
      if (!day.open_time || !day.close_time) {
        toast.error(`${label}: open and close time are required.`);
        return false;
      }
      if (day.open_time >= day.close_time) {
        toast.error(`${label}: open time must be before close time.`);
        return false;
      }
      if (day.break_start && day.break_end && day.break_start >= day.break_end) {
        toast.error(`${label}: break start must be before break end.`);
        return false;
      }
    }
    return true;
  };

  const handleSave = async () => {
    if (!vendorId || !validate()) return;
    setSaving(true);
    try {
      await Promise.all(
        DAYS.map(({ key }) => {
          const day = schedule[key];
          const body = { ...toPayload(day), day_of_week: key };
          return day.id
            ? vendorProfileApi.updateAvailability(vendorId, day.id, toPayload(day))
            : vendorProfileApi.createAvailability(vendorId, body);
        })
      );
      toast.success('Weekly schedule saved.');
      qc.invalidateQueries(['vendor-availability', vendorId]);
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Failed to save schedule.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Availability</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Set your active weekdays and working hours</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-primary" onClick={handleSave} disabled={!vendorId || saving}>
            {saving ? 'Saving…' : 'Save Schedule'}
          </button>
        </div>
      </div>

      {/* Info banner */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', background: 'rgba(59,130,246,0.07)', border: '1px solid rgba(59,130,246,0.18)', borderRadius: 10, padding: '11px 16px', marginBottom: 20, fontSize: 13, color: 'var(--color-info, #3b82f6)' }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginTop: 1, flexShrink: 0 }}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span>Turn on the days you work and set your hours (e.g. Monday–Friday, 9:00 AM–6:00 PM). Customers can only book you during active hours.</span>
      </div>

      {!vendorId ? (
        <div style={{ padding: 48, textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Please create your vendor profile first.</p>
        </div>
      ) : isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[0, 1, 2].map((i) => <SkeletonCard key={i} height={72} />)}
        </div>
      ) : (
        <div className="admin-card">
          <div style={{ padding: '14px 20px', display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn btn-secondary btn-sm" onClick={applyToWeekdays}>
              Copy Monday's hours to Tue–Fri
            </button>
          </div>
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Day</th>
                  <th>Working</th>
                  <th>Open</th>
                  <th>Close</th>
                  <th>Break start</th>
                  <th>Break end</th>
                  <th>Max bookings/day</th>
                </tr>
              </thead>
              <tbody>
                {DAYS.map(({ key, label }) => {
                  const day = schedule[key];
                  return (
                    <tr key={key}>
                      <td style={{ fontWeight: 600 }}>{label}</td>
                      <td>
                        <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                          <input
                            type="checkbox"
                            checked={day.is_working}
                            onChange={(e) => updateDay(key, { is_working: e.target.checked })}
                          />
                        </label>
                      </td>
                      <td>
                        <input
                          className="admin-input"
                          type="time"
                          value={day.open_time}
                          onChange={(e) => updateDay(key, { open_time: e.target.value })}
                          disabled={!day.is_working}
                          style={{ width: 120 }}
                        />
                      </td>
                      <td>
                        <input
                          className="admin-input"
                          type="time"
                          value={day.close_time}
                          onChange={(e) => updateDay(key, { close_time: e.target.value })}
                          disabled={!day.is_working}
                          style={{ width: 120 }}
                        />
                      </td>
                      <td>
                        <input
                          className="admin-input"
                          type="time"
                          value={day.break_start}
                          onChange={(e) => updateDay(key, { break_start: e.target.value })}
                          disabled={!day.is_working}
                          style={{ width: 120 }}
                        />
                      </td>
                      <td>
                        <input
                          className="admin-input"
                          type="time"
                          value={day.break_end}
                          onChange={(e) => updateDay(key, { break_end: e.target.value })}
                          disabled={!day.is_working}
                          style={{ width: 120 }}
                        />
                      </td>
                      <td>
                        <input
                          className="admin-input"
                          type="number"
                          min="1"
                          max="50"
                          value={day.max_bookings_per_day}
                          onChange={(e) => updateDay(key, { max_bookings_per_day: e.target.value })}
                          disabled={!day.is_working}
                          style={{ width: 80 }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
