import { useEffect, useState } from "react";

export function OfflineHint() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [show, setShow] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShow(false);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShow(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (!show) return null;

  return (
    <div className="offline-banner" role="alert" aria-live="polite">
      <span className="offline-message">无法联网，请检查网络连接</span>
      <button 
        className="offline-dismiss" 
        onClick={() => setShow(false)}
        aria-label="关闭离线提示"
      >
        关闭
      </button>
    </div>
  );
}
