# Calendar Import Feature

The Winter Dragon Bot now supports importing calendar events from .ics files and shared calendar links.

## Commands

### `/calendar import file`
Import events from an uploaded .ics calendar file.

**Usage:**
1. Use the command `/calendar import file`
2. Upload a `.ics` calendar file (max 1MB)
3. The bot will parse the file and create reminders for all future events

### `/calendar import link`
Import events from a shared calendar URL.

**Usage:**
1. Use the command `/calendar import link`
2. Provide a URL to a public calendar (e.g., Google Calendar public link)
3. The bot will download and parse the calendar, creating reminders for future events

## Supported Calendar Sources

- **Google Calendar**: Export calendar or use public calendar sharing link
- **Microsoft Outlook/Office 365**: Export to .ics format
- **Apple Calendar**: Export calendar events
- **Any application that exports standard .ics files**

## Features

- Automatically filters to only import future events
- Converts calendar events to personal reminders
- Handles both all-day and timed events
- Supports event descriptions
- File size limit of 1MB for uploads
- Error handling for invalid files or URLs

## Examples

### Sample .ics file format:
```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp//Example Calendar//EN
BEGIN:VEVENT
UID:example-event@example.com
DTSTART:20251225T120000Z
DTEND:20251225T130000Z
SUMMARY:Christmas Lunch
DESCRIPTION:Annual Christmas lunch with family
END:VEVENT
END:VCALENDAR
```

### Google Calendar sharing:
1. Open Google Calendar
2. Click on the calendar you want to share
3. Choose "Settings and sharing"
4. Copy the public calendar URL (ends with `.ics`)
5. Use `/calendar import link` with this URL

## Technical Notes

- Events are converted to reminders using the existing reminder system
- All times are converted to UTC for consistency
- The bot will send you a DM reminder at the event time
- Only future events are imported to avoid spam from past events