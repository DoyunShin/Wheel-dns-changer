import { useCookies, CookiesProvider } from "react-cookie";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import axios from "axios";
import "./App.css";

import { SetDNS } from "./SetDNS";

const Main = () => {
  const navigate = useNavigate();
  const [cookies, setCookie] = useCookies();

  function handleSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    axios
      .post("https://route53.sparcs.net/api/auth", {
        userid: formData.get("userId"),
        userpw: formData.get("userPw"),
      })
      .then((res) => {
        if (res.status === 200) {
          setCookie("sessid", res.data.sessid, { path: "/" });
          navigate("/dns");
        } else if (res.status === 401) {
          console.log(res.data.message);
        } else {
          console.log(res.data.message);
        }
      });
  }
  return (
    <div className="wrapper">
      <text className="title">2024 Winter Wheel Seminar DNS Setting</text>
      <form className="container" onSubmit={handleSubmit}>
        <input name="userId" placeholder="User ID" />
        <input type="password" name="userPw" placeholder="User PW" />
        <button type="submit">Sign In</button>
      </form>
    </div>
  );
};

function App() {
  return (
    <div
      className="App"
      css={{
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <CookiesProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Main />} />
            <Route path="/dns" element={<SetDNS />} />
          </Routes>
        </BrowserRouter>
      </CookiesProvider>
    </div>
  );
}

export default App;
