import { X } from 'lucide-react'
import { useId, useLayoutEffect, useRef, type ReactNode, type RefObject } from 'react'

interface DemoDialogProps {
  variant: 'welcome' | 'drawer'
  title: string
  eyebrow?: string
  onDismiss: () => void
  returnFocusRef?: RefObject<HTMLElement | null>
  children: ReactNode
  footer: ReactNode
}

export function DemoDialog({ variant, title, eyebrow, onDismiss, returnFocusRef, children, footer }: DemoDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const backdropPressed = useRef(false)
  const titleId = useId()

  useLayoutEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    dialog.showModal()
    titleRef.current?.focus({ preventScroll: true })

    return () => {
      dialog.close()
      returnFocusRef?.current?.focus({ preventScroll: true })
    }
  }, [returnFocusRef])

  return (
    <dialog
      ref={dialogRef}
      className={`demo-dialog demo-dialog-${variant}`}
      aria-labelledby={titleId}
      aria-modal="true"
      onCancel={(event) => {
        event.preventDefault()
        onDismiss()
      }}
      onPointerDown={(event) => {
        backdropPressed.current = event.target === event.currentTarget
      }}
      onClick={(event) => {
        if (backdropPressed.current && event.target === event.currentTarget) onDismiss()
        backdropPressed.current = false
      }}
    >
      <div className="demo-dialog-panel">
        <header className="demo-dialog-header">
          <div>
            {eyebrow && <span className="eyebrow">{eyebrow}</span>}
            <h2 ref={titleRef} id={titleId} tabIndex={-1}>{title}</h2>
          </div>
          <button type="button" className="demo-dialog-close" aria-label={`Close ${variant === 'welcome' ? 'welcome' : 'demo guide'}`} onClick={onDismiss}>
            <X size={20} aria-hidden="true" />
          </button>
        </header>
        <div className="demo-dialog-body" role="region" aria-labelledby={titleId} tabIndex={0}>
          {children}
        </div>
        <footer className="demo-dialog-footer">{footer}</footer>
      </div>
    </dialog>
  )
}
