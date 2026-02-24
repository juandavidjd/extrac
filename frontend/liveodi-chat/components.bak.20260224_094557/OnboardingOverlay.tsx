"use client";

import { useState } from "react";

interface ODIProfile {
  industry: "motos" | "salud" | "otro";
  hasBusiness: boolean;
  firstVisit: string;
}

interface Props {
  onComplete: (profile: ODIProfile) => void;
}

export default function OnboardingOverlay({ onComplete }: Props) {
  const [step, setStep] = useState<1 | 2>(1);
  const [industry, setIndustry] = useState<ODIProfile["industry"] | null>(null);
  const [fade, setFade] = useState(false);

  const selectIndustry = (ind: ODIProfile["industry"]) => {
    setIndustry(ind);
    setFade(true);
    setTimeout(() => {
      setFade(false);
      setStep(2);
    }, 300);
  };

  const selectBusiness = (has: boolean) => {
    const profile: ODIProfile = {
      industry: industry!,
      hasBusiness: has,
      firstVisit: new Date().toISOString(),
    };
    localStorage.setItem("odi_profile", JSON.stringify(profile));
    onComplete(profile);
  };

  return (
    <div className="fixed inset-0 z-[70] bg-black flex flex-col items-center justify-center">
      <div className={`transition-opacity duration-300 ${fade ? "opacity-0" : "opacity-100"}`}>
        {step === 1 && (
          <div className="text-center px-6">
            <p className="text-white text-2xl mb-12 font-light tracking-wide">
              {"\u00BF"}Qu{"\u00E9"} te trae aqu{"\u00ED"}?
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => selectIndustry("motos")}
                className="px-8 py-4 border border-white/20 text-white/80 rounded-lg hover:border-emerald-500/60 hover:text-white transition-all duration-200 text-lg"
              >
                Repuestos de motos
              </button>
              <button
                onClick={() => selectIndustry("salud")}
                className="px-8 py-4 border border-white/20 text-white/80 rounded-lg hover:border-emerald-500/60 hover:text-white transition-all duration-200 text-lg"
              >
                Salud
              </button>
              <button
                onClick={() => selectIndustry("otro")}
                className="px-8 py-4 border border-white/20 text-white/80 rounded-lg hover:border-emerald-500/60 hover:text-white transition-all duration-200 text-lg"
              >
                Otro
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="text-center px-6">
            <p className="text-white text-2xl mb-12 font-light tracking-wide">
              {"\u00BF"}Tienes negocio propio?
            </p>
            <div className="flex gap-6 justify-center">
              <button
                onClick={() => selectBusiness(true)}
                className="px-12 py-4 border border-white/20 text-white/80 rounded-lg hover:border-emerald-500/60 hover:text-white transition-all duration-200 text-lg"
              >
                S{"\u00ED"}
              </button>
              <button
                onClick={() => selectBusiness(false)}
                className="px-12 py-4 border border-white/20 text-white/80 rounded-lg hover:border-emerald-500/60 hover:text-white transition-all duration-200 text-lg"
              >
                No
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
