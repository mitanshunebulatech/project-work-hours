import * as React from 'react'
import * as AvatarPrimitive from '@radix-ui/react-avatar'
import { cn } from '@/lib/utils'

export const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn('relative flex h-8 w-8 shrink-0 overflow-hidden rounded-full', className)}
    {...props}
  />
))
Avatar.displayName = 'Avatar'

export const AvatarImage = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image ref={ref} className={cn('aspect-square h-full w-full', className)} {...props} />
))
AvatarImage.displayName = 'AvatarImage'

export const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-nebula-500 to-nebula-700 text-xs font-bold text-white',
      className
    )}
    {...props}
  />
))
AvatarFallback.displayName = 'AvatarFallback'

/** Convenience wrapper: renders initials on a brand-gradient circle. */
export function UserAvatar({ name, className, size = 32 }: { name?: string; className?: string; size?: number }) {
  const initial = name?.trim()?.[0]?.toUpperCase() || '?'
  return (
    <Avatar className={className} style={{ width: size, height: size }}>
      <AvatarFallback style={{ fontSize: size * 0.4 }}>{initial}</AvatarFallback>
    </Avatar>
  )
}
