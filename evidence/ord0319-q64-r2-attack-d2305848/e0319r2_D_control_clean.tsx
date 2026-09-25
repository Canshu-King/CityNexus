export function X() { const note = {failureReason: {from: "device", text: "这台设备自己的读数"}};
  return <code data-testid="plan-ai-reason">{note.failureReason.text}</code>; }
