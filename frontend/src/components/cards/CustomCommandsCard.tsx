
import { Card, Badge } from '../daisyui'

export function CustomCommandsCard() {
  return (
    <Card className="bg-base-200 shadow-xl hover:shadow-2xl transition-all">
      <Badge variant="accent" className="mb-2">Customizable</Badge>
      <h3 className="card-title">Custom Commands</h3>
      <p>Create your own server-specific commands with custom responses, embed messages, and automatic triggers.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/custom-commands" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </Card>
  );
}
