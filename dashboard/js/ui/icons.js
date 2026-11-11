// Nap bo icon SVG (assets/icons.svg) vao trang de cac the <use href="#i-..."> hoat dong
export async function loadIcons(){
  try{
    const res=await fetch("assets/icons.svg");
    if(!res.ok)throw new Error("HTTP "+res.status);
    document.body.insertAdjacentHTML("afterbegin",await res.text());
  }catch(e){console.error("Khong nap duoc icons.svg",e);}
}
