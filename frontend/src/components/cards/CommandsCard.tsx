
import { Card, Badge } from '../daisyui'

export function CommandsCard() {
  return (
    <Card className="bg-base-200 shadow-xl hover:shadow-2xl transition-all">
      <Badge variant="success" className="mb-2">Entertainment</Badge>
      <h3 className="card-title">Fun & Games</h3>
      <p>Variety of fun commands, games, memes, and utilities to keep your server members engaged and entertained.</p>
      <div className="card-actions justify-end mt-4">
        <a href="/features/fun" className="btn btn-sm btn-primary">Learn More</a>
      </div>
    </Card>
  );
}
