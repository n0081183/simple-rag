import Image from "next/image";
import { cn } from "@/lib/utils";

export function CortexLogo({ className, size = 32 }: { className?: string; size?: number }) {
  return (
    <Image
      src="/logo.svg"
      alt=""
      width={size}
      height={size}
      className={cn("shrink-0", className)}
      priority
    />
  );
}
