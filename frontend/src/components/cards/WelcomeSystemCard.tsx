
import { Card, Badge } from '../daisyui'

export function WelcomeSystemCard() {
  return (
    <Card className="bg-base-200 shadow-xl hover:shadow-2xl transition-all">
      <Badge variant="info" className="mb-2">Community</Badge>
      <h3 className="card-title">Welcome System</h3>
      <p>Customize welcome messages with embed templates, role assignments, and welcome channels to greet new members.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/welcome" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </Card>
  );
}
