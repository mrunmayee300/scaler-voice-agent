"use client";

import { useMemo, useState } from "react";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { bookMeeting, getAvailableSlots } from "@/lib/api";

const TIMEZONE = "Asia/Kolkata";
const TIME_OPTIONS = Array.from({ length: 25 }, (_, i) => {
  const hour = 8 + Math.floor(i / 2);
  const minute = i % 2 === 0 ? "00" : "30";
  if (hour > 20 || (hour === 20 && minute === "30")) return null;
  return `${String(hour).padStart(2, "0")}:${minute}`;
}).filter(Boolean) as string[];

type PreferenceWindow = {
  id: string;
  date: string;
  startTime: string;
  endTime: string;
};

type Slot = { start: string; end: string; available: boolean };

function formatDateInput(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function nextWeekday(offset: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  while (d.getDay() === 0 || d.getDay() === 6) {
    d.setDate(d.getDate() + 1);
  }
  return formatDateInput(d);
}

function defaultWindows(): PreferenceWindow[] {
  return [
    { id: "1", date: nextWeekday(1), startTime: "09:00", endTime: "18:00" },
    { id: "2", date: nextWeekday(2), startTime: "09:00", endTime: "18:00" },
  ];
}

function formatSlotLabel(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const datePart = start.toLocaleDateString("en-IN", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: TIMEZONE,
  });
  const timeFmt: Intl.DateTimeFormatOptions = {
    hour: "numeric",
    minute: "2-digit",
    timeZone: TIMEZONE,
  };
  return `${datePart} · ${start.toLocaleTimeString("en-IN", timeFmt)} – ${end.toLocaleTimeString("en-IN", timeFmt)}`;
}

function formatDayHeading(dateKey: string): string {
  const d = new Date(`${dateKey}T12:00:00`);
  return d.toLocaleDateString("en-IN", {
    weekday: "long",
    month: "long",
    day: "numeric",
    timeZone: TIMEZONE,
  });
}

export function BookingForm() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [windows, setWindows] = useState<PreferenceWindow[]>(defaultWindows);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [groupedSlots, setGroupedSlots] = useState<Record<string, Slot[]>>({});
  const [selectedSlot, setSelectedSlot] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [booked, setBooked] = useState(false);

  const minDate = useMemo(() => formatDateInput(new Date()), []);

  const updateWindow = (id: string, patch: Partial<PreferenceWindow>) => {
    setWindows((prev) =>
      prev.map((w) => {
        if (w.id !== id) return w;
        const next = { ...w, ...patch };
        if (next.startTime >= next.endTime) {
          const later = TIME_OPTIONS.find((t) => t > next.startTime);
          if (later) next.endTime = later;
        }
        return next;
      })
    );
    setSlots([]);
    setGroupedSlots({});
    setSelectedSlot("");
    setBooked(false);
  };

  const addWindow = () => {
    const last = windows[windows.length - 1];
    const nextDate = last ? last.date : nextWeekday(1);
    setWindows((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        date: nextDate,
        startTime: "09:00",
        endTime: "18:00",
      },
    ]);
  };

  const removeWindow = (id: string) => {
    if (windows.length <= 1) return;
    setWindows((prev) => prev.filter((w) => w.id !== id));
    setSlots([]);
    setGroupedSlots({});
    setSelectedSlot("");
  };

  const validateWindows = (): string | null => {
    for (const w of windows) {
      if (!w.date) return "Please pick a date for each preference.";
      if (w.date < minDate) return "Preference dates must be today or later.";
      if (w.startTime >= w.endTime) return "End time must be after start time on each day.";
      if (w.startTime < "08:00" || w.endTime > "20:00") {
        return "Interview windows must stay between 8:00 AM and 8:00 PM.";
      }
    }
    return null;
  };

  const fetchSlots = async () => {
    const err = validateWindows();
    if (err) {
      setMessage(err);
      return;
    }
    setLoading(true);
    setMessage("");
    setSelectedSlot("");
    setBooked(false);
    try {
      const data = await getAvailableSlots({
        timezone: TIMEZONE,
        windows: windows.map((w) => ({
          date: w.date,
          start_time: w.startTime,
          end_time: w.endTime,
        })),
      });
      const found = data.slots || [];
      setSlots(found);
      setGroupedSlots(data.grouped_by_date || {});
      if (!found.length) {
        setMessage(
          "No open slots in your preferred times. Try different dates, wider time ranges, or another day."
        );
      } else {
        setMessage(`${found.length} available slot${found.length === 1 ? "" : "s"} found.`);
      }
    } catch {
      setMessage("Failed to fetch availability. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleBook = async () => {
    if (!email || !name || !selectedSlot) {
      setMessage("Please enter your details and select a slot.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setMessage("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const result = await bookMeeting({
        start_time: selectedSlot,
        attendee_email: email,
        attendee_name: name,
        notes: notes || undefined,
        timezone: TIMEZONE,
      });
      if (result.success) {
        setBooked(true);
        setMessage(result.message || "Interview booked successfully.");
        setSlots([]);
        setGroupedSlots({});
        setSelectedSlot("");
      } else {
        setMessage(result.message || "Booking failed. Please pick another slot.");
      }
    } catch {
      setMessage("Booking failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const sortedDays = Object.keys(groupedSlots).sort();

  return (
    <div className="p-4 space-y-4 max-w-lg mx-auto text-sm">
      <p className="text-muted-foreground">
        30-minute interviews · {TIMEZONE.replace("_", " ")} · Weekdays · 8 AM – 8 PM
      </p>

      <div className="space-y-2">
        <Input placeholder="Your full name" value={name} onChange={(e) => setName(e.target.value)} />
        <Input
          placeholder="Your email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          placeholder="Notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="font-medium">When are you available?</p>
          <Button type="button" variant="ghost" size="sm" onClick={addWindow} className="h-8 px-2">
            <Plus className="h-4 w-4 mr-1" />
            Add day
          </Button>
        </div>

        {windows.map((w) => (
          <div key={w.id} className="rounded-md border border-border p-3 space-y-2 bg-background/50">
            <div className="flex gap-2 items-center">
              <Input
                type="date"
                min={minDate}
                value={w.date}
                onChange={(e) => updateWindow(w.id, { date: e.target.value })}
                className="flex-1"
              />
              {windows.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeWindow(w.id)}
                  className="shrink-0 text-muted-foreground"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
            <div className="flex gap-2 items-center">
              <label className="text-xs text-muted-foreground w-8">From</label>
              <select
                value={w.startTime}
                onChange={(e) => updateWindow(w.id, { startTime: e.target.value })}
                className="flex-1 h-9 rounded-md border border-input bg-background px-2 text-sm"
              >
                {TIME_OPTIONS.map((t) => (
                  <option key={`${w.id}-s-${t}`} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <label className="text-xs text-muted-foreground w-6">To</label>
              <select
                value={w.endTime}
                onChange={(e) => updateWindow(w.id, { endTime: e.target.value })}
                className="flex-1 h-9 rounded-md border border-input bg-background px-2 text-sm"
              >
                {TIME_OPTIONS.filter((t) => t > w.startTime).map((t) => (
                  <option key={`${w.id}-e-${t}`} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>

      <Button onClick={fetchSlots} disabled={loading} variant="secondary" className="w-full">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Check Availability"}
      </Button>

      {sortedDays.length > 0 && (
        <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
          <p className="font-medium text-muted-foreground">Pick a time</p>
          {sortedDays.map((day) => (
            <div key={day} className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {formatDayHeading(day)}
              </p>
              {(groupedSlots[day] || []).map((slot) => (
                <button
                  key={slot.start}
                  type="button"
                  onClick={() => setSelectedSlot(slot.start)}
                  className={`w-full text-left px-3 py-2 rounded-md border transition-colors ${
                    selectedSlot === slot.start
                      ? "border-primary bg-primary/10"
                      : "border-border hover:bg-accent"
                  }`}
                >
                  {formatSlotLabel(slot.start, slot.end)}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}

      {!sortedDays.length && slots.length > 0 && (
        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {slots.map((slot) => (
            <button
              key={slot.start}
              type="button"
              onClick={() => setSelectedSlot(slot.start)}
              className={`w-full text-left px-3 py-2 rounded-md border ${
                selectedSlot === slot.start
                  ? "border-primary bg-primary/10"
                  : "border-border hover:bg-accent"
              }`}
            >
              {formatSlotLabel(slot.start, slot.end)}
            </button>
          ))}
        </div>
      )}

      <Button
        onClick={handleBook}
        disabled={loading || !selectedSlot || booked}
        className="w-full"
      >
        {booked ? "Booked" : "Confirm Booking"}
      </Button>

      {message && (
        <p
          className={`text-sm ${booked ? "text-green-600 dark:text-green-400" : "text-muted-foreground"}`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
