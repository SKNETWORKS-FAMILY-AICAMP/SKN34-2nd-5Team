import { useEffect } from "react";
import { useLocation } from "react-router";

// SPA navigation doesn't reset scroll position the way a full page load
// does — without this, clicking a link from partway down a long list opens
// the next screen still scrolled to that same offset. Watches pathname only
// (not search params), so in-page filtering/sorting doesn't jump the scroll.
function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}

export default ScrollToTop;
