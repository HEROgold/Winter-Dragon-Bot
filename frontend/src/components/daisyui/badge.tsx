import * as React from "react";

import { cn } from "@/lib/utils";

type BadgeVariant = "primary" | "secondary" | "accent" | "info" | "success" | "warning" | "error" | "ghost" | "outline";
type BadgeSize = "lg" | "md" | "sm" | "xs";

interface BadgeProps extends React.ComponentProps<"div"> {
  variant?: BadgeVariant;
  size?: BadgeSize;
}

function Badge({ className, variant = "primary", size = "md", ...props }: BadgeProps) {
  return (
    <div
      data-slot="badge"
      className={cn(
        "badge",
        variant && `badge-${variant}`,
        size && `badge-${size}`,
        className
      )}
      {...props}
    />
  );
}

export { Badge, type BadgeProps, type BadgeVariant, type BadgeSize };
