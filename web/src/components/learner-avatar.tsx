import { Bird, Cat, Dog, Fish, Rabbit, Turtle, type LucideIcon } from "lucide-react";

import type { Avatar } from "@/lib/profile";
import type { Learner } from "@/lib/types";
import { cn } from "@/lib/utils";

export const AVATAR_ICONS: Record<Avatar, LucideIcon> = {
  owl: Bird,
  cat: Cat,
  dog: Dog,
  rabbit: Rabbit,
  turtle: Turtle,
  fish: Fish,
};

export function AvatarIcon({
  avatar,
  accent,
  className,
}: {
  avatar: string;
  accent?: string;
  className?: string;
}) {
  const Icon = AVATAR_ICONS[avatar as Avatar] ?? Bird;
  return (
    <span
      data-accent={accent}
      className={cn(
        "grid shrink-0 place-items-center rounded-full bg-primary-soft text-primary ring-2 ring-background",
        className,
      )}
      aria-hidden
    >
      <Icon className="size-[55%]" strokeWidth={2.25} />
    </span>
  );
}

export function LearnerAvatar({ learner, className }: { learner: Learner; className?: string }) {
  return <AvatarIcon avatar={learner.appearance.avatar} className={className} />;
}
