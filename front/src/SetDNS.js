import { useCookies } from "react-cookie";
import Dropdown from "react-dropdown";
import axios from "axios";
import { useState, useEffect } from "react";
import { useNavigate, redirect } from "react-router-dom";
import "./SetDNS.css";

export const SetDNS = () => {
  const navigate = useNavigate();
  const [cookies, removeCookie] = useCookies(["sessid"]);
  const [firstDNS, setFirstDNS] = useState("기본DNS");
  const [secondDNS, setSecondDNS] = useState("보조DNS");
  const [firstData, setFirstData] = useState({ type: "", value: "" });
  const [secondData, setSecondData] = useState({ type: "", value: "" });
  const [availableTypes, setAvailableTypes] = useState([""]);
  const [resText, setResText] = useState("");
  const [firstType, setFirstType] = useState(availableTypes[0]);
  const [secondType, setSecondType] = useState(availableTypes[0]);

  useEffect(() => {
    const intervalSession = setInterval(() => {
      axios
        .get("https://route53.sparcs.net/api/auth", {
          headers: { sessid: cookies.sessid },
        })
        .then((res) => {
          if (res.status === 200) {
          } else if (res.status === 401) {
            redirect("/");
          } else {
            console.log(res.data.message);
          }
        });
    }, 2000);
    return () => clearInterval(intervalSession);
  }, [cookies.sessid]);
  useEffect(() => {
    axios
      .get("https://route53.sparcs.net/api/dns", {
        headers: { sessid: cookies.sessid },
      })
      .then((res) => {
        if (res.status === 200) {
          const list = Object.keys(res.data["data"]);
          setAvailableTypes(res.data["available_types"]);
          setFirstType(res.data["available_types"][0]);
          setSecondType(res.data["available_types"][0]);
          setFirstDNS(list[0]);
          setSecondDNS(list[1]);
          setFirstData({
            type: res.data["data"][list[0]].type,
            value: res.data["data"][list[0]].value,
          });
          setSecondData({
            type: res.data["data"][list[1]].type,
            value: res.data["data"][list[1]].value,
          });
        } else if (res.status === 500) {
          console.log(res.data.message);
          redirect("/");
        } else {
          console.log(res.data.message);
          redirect("/");
        }
      });
  }, []);
  const handleSubmit = (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    if (firstType === undefined) {
      setFirstType({ value: availableTypes[0] });
    }
    if (secondType === undefined) {
      setSecondType({ value: availableTypes[0] });
    }
    axios
      .post(
        "https://route53.sparcs.net/api/dns",
        {
          [firstDNS]: {
            type: firstType.value,
            value: formData.get("firstValue"),
          },
          [secondDNS]: {
            type: secondType,
            value: formData.get("secondValue"),
          },
        },
        {
          headers: { sessid: cookies.sessid },
        }
      )
      .then((res) => {
        if (res.status === 200) {
          setResText(res.data.message);
        } else if (res.status === 500) {
          setResText(res.data.message);
          console.log(res.data.message);
        } else {
          console.log(res.data.message);
        }
      });
  };

  return (
    <div>
      <text className="title">2024 Winter Wheel Seminar DNS Setting</text>
      <form className="container" onSubmit={handleSubmit}>
        <div className="content">
          <text className="header">DNS</text>
          <text className="header" key="firstDNS">
            {firstDNS}
          </text>
          <text className="header" key="secondDNS">
            {secondDNS}
          </text>
        </div>
        <div className="content">
          <text className="header">Value</text>
          <input
            className="header1"
            key="firstValue"
            name="firstValue"
            placeholder={firstData.value}
          />
          <input
            className="header1"
            key="secondValue"
            name="secondValue"
            placeholder={secondData.value}
          />
        </div>
        <div className="content">
          <text className="header">Type</text>
          <Dropdown
            className="dropdown"
            value={firstType}
            onChange={(value, label) => {
              setFirstType(value);
            }}
            placeholder="Select an option"
            options={availableTypes}
          />
          <Dropdown
            className="dropdown"
            value={secondType}
            onChange={(value, label) => {
              setSecondType(value);
            }}
            placeholder="Select an option"
            options={availableTypes}
          />
        </div>
        <button className="button" type="submit">
          Save
        </button>
        <button
          className="button"
          onClick={() => {
            removeCookie("sessid");
            axios.delete("https://route53.sparcs.net/api/auth", {
              headers: { sessid: cookies.sessid },
            });
            navigate("/");
          }}
        >
          Log Out
        </button>
      </form>
      <text className="footer">{resText}</text>
    </div>
  );
};
