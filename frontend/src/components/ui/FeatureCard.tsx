import { Link } from "react-router-dom";

export interface FeatureCardProps {
  title: string;
  description: string;
  badgeText: string;
  badgeColor: "primary" | "secondary" | "accent" | "info" | "success" | "warning" | "error";
  link: string;
  linkText?: string;
}

/**
 * A reusable card component for displaying features.
 * 
 * @param {FeatureCardProps} props - The properties to configure the feature card
 * @returns {JSX.Element} The rendered feature card
 */
export function FeatureCard({
  title,
  description,
  badgeText,
  badgeColor,
  link,
  linkText = "Learn More",
}: FeatureCardProps) {
  return (
    <div className="card bg-base-200 shadow-xl hover:shadow-2xl transition-all">
      <div className="card-body">
        <div className={`badge badge-${badgeColor} mb-2`}>{badgeText}</div>
        <h3 className="card-title">{title}</h3>
        <p>{description}</p>
        <div className="card-actions justify-end mt-4">
          <Link to={link} className="btn btn-sm btn-primary">
            {linkText}
          </Link>
        </div>
      </div>
    </div>
  );
}
