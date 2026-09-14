import { ConnectBox } from "@phantom/react-sdk";

export function Callback() {
  return (
    <div className="app" style={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <ConnectBox />
    </div>
  );
}
