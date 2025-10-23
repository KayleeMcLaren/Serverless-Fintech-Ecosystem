import React from 'react';

/**
 * A simple, centered loading spinner using Tailwind CSS.
 */
function Spinner() {
  return (
    // Centers the spinner with a top/bottom margin
    <div className="flex justify-center items-center my-6" aria-label="Loading...">
      {/* The spinner element: a spinning circle with a blue border */}
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-blue"></div>
    </div>
  );
}

export default Spinner;