"use client";

import { useState, useSyncExternalStore } from "react";

const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const windows = ["Morning", "Afternoon", "Either works"];

function localDateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function Calendar({ selected, onSelect }: { selected: string; onSelect: (date: string) => void }) {
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const lastDay = new Date(today);
  lastDay.setDate(lastDay.getDate() + 90);
  const firstWeekday = new Date(month.getFullYear(), month.getMonth(), 1).getDay();
  const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const dates = Array.from({ length: firstWeekday + daysInMonth }, (_, index) => index - firstWeekday + 1);
  const atCurrentMonth = month.getFullYear() === today.getFullYear() && month.getMonth() === today.getMonth();
  const atLastMonth = month.getFullYear() === lastDay.getFullYear() && month.getMonth() === lastDay.getMonth();

  function changeMonth(delta: number) {
    setMonth(new Date(month.getFullYear(), month.getMonth() + delta, 1));
  }

  return <div className="booking-calendar">
    <div className="calendar-heading"><strong>{new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(month)}</strong><div><button type="button" onClick={() => changeMonth(-1)} disabled={atCurrentMonth}>Previous month</button><button type="button" onClick={() => changeMonth(1)} disabled={atLastMonth}>Next month</button></div></div>
    <div className="calendar-grid" role="group" aria-label="Preferred demo date">
      {weekdays.map((day) => <span className="calendar-weekday" key={day}>{day}</span>)}
      {dates.map((day, index) => {
        if (day < 1) return <span key={`blank-${index}`} aria-hidden="true" />;
        const date = new Date(month.getFullYear(), month.getMonth(), day);
        const key = localDateKey(date);
        const unavailable = date < today || date > lastDay;
        return <button key={key} type="button" disabled={unavailable} aria-pressed={selected === key} aria-label={new Intl.DateTimeFormat(undefined, { dateStyle: "full" }).format(date)} onClick={() => onSelect(key)}>{day}</button>;
      })}
    </div>
    <p>Choose a preferred date. This is a request, not a confirmed appointment.</p>
  </div>;
}

function BookingCalendar(props: { selected: string; onSelect: (date: string) => void }) {
  const mounted = useSyncExternalStore(() => () => {}, () => true, () => false);
  return mounted ? <Calendar {...props} /> : <div className="booking-calendar-loading">Loading the calendar…</div>;
}

export function DemoBookingForm() {
  const [preferredDate, setPreferredDate] = useState("");
  return <form className="booking-form" onSubmit={(event) => event.preventDefault()}>
    <div className="booking-fields">
      <label>Full name<input name="name" type="text" autoComplete="name" required /></label>
      <label>Work email<input name="email" type="email" autoComplete="email" required /></label>
      <label>Company<input name="company" type="text" autoComplete="organization" required /></label>
      <label>What would you like to cover? <span>(optional)</span><textarea name="message" rows={4} placeholder="For example, assets and vulnerabilities, third-party risk, or evidence review" /></label>
    </div>
    <fieldset className="booking-preference"><legend>Preferred time in your local time zone</legend><div>{windows.map((window) => <label key={window}><input type="radio" name="window" value={window} required />{window}</label>)}</div></fieldset>
    <div className="calendar-label">Preferred date</div>
    <BookingCalendar selected={preferredDate} onSelect={setPreferredDate} />
    <input type="hidden" name="preferredDate" value={preferredDate} />
    <p className="booking-status" role="status">Demo scheduling is being set up. This form does not send your details or reserve a time yet.</p>
    <button className="button button-primary" type="submit" disabled>Request demo</button>
  </form>;
}
