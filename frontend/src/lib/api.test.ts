import { describe, expect, it } from "vitest";
import { assetUrl } from "./api";

describe("assetUrl", () => {
  it("points uploaded posters at the API host, not the site host", () => {
    expect(assetUrl("/media/posters/abc.png")).toBe("http://localhost:8000/media/posters/abc.png");
  });
  it("leaves external and empty urls alone", () => {
    expect(assetUrl("https://image.tmdb.org/t/p/w500/x.jpg")).toBe("https://image.tmdb.org/t/p/w500/x.jpg");
    expect(assetUrl(null)).toBeNull();
    expect(assetUrl("")).toBeNull();
  });
});
