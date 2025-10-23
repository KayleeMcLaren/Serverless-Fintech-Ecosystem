import React from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

/**
 * A reusable confirmation modal component.
 *
 * @param {object} props
 * @param {boolean} props.isOpen - Whether the modal is open or not.
 * @param {function} props.onClose - Function to call when closing (Cancel, X, or backdrop click).
 * @param {function} props.onConfirm - Function to call when the confirm button is clicked.
 * @param {string} props.title - The title text for the modal.
 * @param {React.ReactNode} props.children - The content/body text of the modal.
 * @param {string} [props.confirmText="Confirm"] - Text for the confirm button.
 * @param {string} [props.cancelText="Cancel"] - Text for the cancel button.
 * @param {string} [props.confirmVariant="danger"] - 'danger' (red) or 'primary' (blue) for confirm button.
 */
function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  children,
  confirmText = "Confirm",
  cancelText = "Cancel",
  confirmVariant = "danger" // 'danger' or 'primary'
}) {
  if (!isOpen) {
    return null; // Don't render anything if not open
  }

  // Determine button color based on variant
  const confirmClasses = `px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2
    ${confirmVariant === 'danger'
      ? 'bg-accent-red hover:bg-accent-red-dark focus:ring-accent-red'
      : 'bg-primary-blue hover:bg-primary-blue-dark focus:ring-primary-blue'
    }`;
  
  const cancelClasses = `px-4 py-2 text-sm font-medium text-neutral-700 bg-neutral-100 rounded-md border border-neutral-300 hover:bg-neutral-200 focus:outline-none focus:ring-2 focus:ring-neutral-400 focus:ring-offset-2`;

  return (
    // Backdrop: full screen, fixed, semi-transparent, high z-index
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" // `bg-black/50` is Tailwind for black with 50% opacity
      onClick={onClose} // Close modal on backdrop click
      aria-modal="true"
      role="dialog"
    >
      {/* Modal Panel: stop propagation so clicking panel doesn't close it */}
      <div
        className="relative w-full max-w-md p-6 bg-white rounded-lg shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button (X icon) */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-full text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-400"
          aria-label="Close modal"
        >
          <XMarkIcon className="h-6 w-6" />
        </button>

        {/* Title */}
        <h3 className="text-lg font-semibold text-neutral-800" id="modal-title">
          {title}
        </h3>

        {/* Content/Body */}
        <div className="mt-2">
          <p className="text-sm text-neutral-600">
            {children}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onClose} className={cancelClasses}>
            {cancelText}
          </button>
          <button onClick={onConfirm} className={confirmClasses}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmModal;