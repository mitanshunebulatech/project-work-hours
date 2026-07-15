import LeaveCalendarWidget from '@/components/LeaveCalendarWidget'

export default function LeaveCalendar() {
  return (
    <div className="p-8 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">Leave Calendar</h1>
          <p className="text-sm text-muted-foreground mt-1">Org-wide view of approved leave</p>
        </div>
      </div>
      <LeaveCalendarWidget />
    </div>
  )
}
