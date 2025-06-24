
import { Card, Badge } from '../daisyui'

export function LoggingCard() {
  return (
    <Card className="bg-base-200 shadow-xl hover:shadow-2xl transition-all">
      <Badge variant="warning" className="mb-2">Admin</Badge>
      <h3 className="card-title">Advanced Logging</h3>
      <p>Comprehensive logging system for all server events including message edits, deletions, member joins/leaves, and moderation actions.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/logging" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </Card>
  );
}
