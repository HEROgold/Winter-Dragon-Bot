import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/daisyui/card";
import { Badge } from "@/components/daisyui/badge";

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
}: FeatureCardProps) {  return (
    <Card className="bg-base-200 shadow-xl hover:shadow-2xl transition-all">
      <CardHeader>
        <Badge variant={badgeColor} className="mb-2">{badgeText}</Badge>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{description}</p>
      </CardContent>
      <CardFooter className="justify-end">
        <Link to={link} className="btn btn-sm btn-primary">
          {linkText}
        </Link>
      </CardFooter>
    </Card>
  );
}
