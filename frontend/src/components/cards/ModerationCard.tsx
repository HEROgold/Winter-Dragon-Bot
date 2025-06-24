
import { Card, Badge } from '../daisyui'

export function ModerationCard() {
  return (
    <Card className="bg-base-200 shadow-xl hover:shadow-2xl transition-all">
      <Badge variant="primary" className="mb-2">Core</Badge>
      <h3 className="card-title">Moderation Tools</h3>
      <p>Complete suite of moderation commands to keep your server safe and organized. Ban, kick, mute, warn users with logging.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/moderation" className="btn btn-sm btn-primary">
          Learn More
        </a>
      </div>
    </Card>
  );
}
