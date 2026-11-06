/**
 * Custom hook for scroll-triggered animations
 * Uses Intersection Observer API to detect when elements enter viewport
 */

import { useEffect, useRef, useState } from 'react';

export const useScrollAnimation = (options = {}) => {
  const elementRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        // Trigger animation when element is in viewport
        if (entry.isIntersecting) {
          setIsVisible(true);
          // Optional: stop observing after first trigger
          if (options.once !== false) {
            observer.unobserve(entry.target);
          }
        } else if (options.once === false) {
          // Re-trigger animation when scrolling back
          setIsVisible(false);
        }
      },
      {
        threshold: options.threshold || 0.1, // Trigger when 10% visible
        rootMargin: options.rootMargin || '0px',
        ...options
      }
    );

    const currentElement = elementRef.current;
    if (currentElement) {
      observer.observe(currentElement);
    }

    return () => {
      if (currentElement) {
        observer.unobserve(currentElement);
      }
    };
  }, [options]);

  return [elementRef, isVisible];
};

export default useScrollAnimation;
