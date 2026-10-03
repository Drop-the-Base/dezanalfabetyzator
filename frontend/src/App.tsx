import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LiveProvider } from "./lib/live";
import { SessionProvider, useSession } from "./lib/session";
import { Mascot, ToastProvider } from "./components/ui";
import Corrections from "./pages/Corrections";
import Feed from "./pages/Feed";
import Login from "./pages/Login";
import NewStory from "./pages/NewStory";
import Story from "./pages/Story";
import Trending from "./pages/Trending";

function Routed() {
  const { user, loading } = useSession();
  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <Mascot size={72} thinking />
      </div>
    );
  }
  if (!user) return <Login />;
  return (
    <LiveProvider enabled>
      <Routes>
        <Route path="/" element={<Feed />} />
        <Route path="/na-topie" element={<Trending />} />
        <Route path="/poprawki" element={<Corrections />} />
        <Route path="/nowa" element={<NewStory />} />
        <Route path="/historia/:id" element={<Story />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </LiveProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <ToastProvider>
          <Routed />
        </ToastProvider>
      </SessionProvider>
    </BrowserRouter>
  );
}
