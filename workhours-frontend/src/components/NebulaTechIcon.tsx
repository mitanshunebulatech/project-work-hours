/**
 * The NebulaTech icon mark (orbit/swoosh symbol), extracted from the real
 * site's src/components/molecules/Logo.tsx — that file is a full lockup
 * (icon + "NebulaTech" wordmark spelled out in SVG paths, 242x54), but
 * every place this app shows a logo is a small square badge (nav header,
 * login/change-password brand mark), so only the icon portion (the first
 * two <path> elements, original viewBox 0 0 58 54) is used here, re-scaled
 * to its own tight viewBox. Colors are the real brand ones from the
 * source file (#F65403 orange, #1A3B70 navy) — same values already used
 * for the app's orange/navy theme tokens, so this drops in without any
 * clash.
 */
export default function NebulaTechIcon({ size = 20, className }: { size?: number; className?: string }) {
  // Real aspect ratio is 58:54 (~1.074:1) — height derived from size so the
  // mark is never stretched, matching how UserAvatar sizes itself via
  // explicit width/height rather than caller-supplied Tailwind classes.
  const height = size * (54 / 58)
  return (
    <svg
      viewBox="0 0 58 54"
      width={size}
      height={height}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path
        d="M26.2649 5.72086V21.4692L31.7976 27.695V5.72086C35.5883 6.16496 39.2126 7.53013 42.3543 9.6972L46.0356 5.51784C41.1004 1.93827 35.1616 0.00731104 29.0649 2.07195e-05C22.9683 -0.0072696 17.0248 1.90948 12.0811 5.47724L15.7515 9.65389C18.8838 7.50699 22.4926 6.15693 26.2649 5.72086Z"
        fill="#F65403"
      />
      <path
        d="M52.1472 11.5027C51.5373 10.6955 50.884 9.922 50.1902 9.18566L48.4957 7.27734L44.79 11.4215L46.5197 13.3677C47.1908 14.1106 47.8095 14.8993 48.3712 15.7281C51.3672 20.0572 52.8179 25.2693 52.4894 30.5238C52.1608 35.7783 50.0722 40.769 46.5603 44.6912C45.9658 45.3546 45.3332 45.9828 44.6655 46.5725L32.7419 33.217L29.0362 29.0674L13.3718 11.5298L9.60929 7.32606L7.91751 9.14236C7.20844 9.89004 6.54325 10.6781 5.92528 11.5027C1.76816 16.9587 -0.317644 23.7131 0.0392554 30.563C0.396155 37.413 3.1726 43.914 7.8742 48.9085C8.46159 49.5365 9.07062 50.1401 9.71485 50.7058C10.4515 51.3656 11.2222 51.9863 12.0238 52.5654C12.7077 53.0635 13.4178 53.5291 14.1541 53.9621L17.9084 49.7476C17.1482 49.3354 16.41 48.8836 15.697 48.3942C14.8912 47.8394 14.1218 47.2337 13.3934 46.5806C9.1199 42.7732 6.38471 37.5355 5.70227 31.8528C5.01984 26.17 6.4372 20.4337 9.68778 15.7227L25.3225 33.2305L29.0362 37.3882L40.1072 49.7801L43.8697 54C44.6385 53.5426 45.3774 53.0581 46.0893 52.5329C46.8797 51.9591 47.6322 51.3501 48.3576 50.7085C49.0154 50.1266 49.638 49.5121 50.2524 48.8679C54.9327 43.8701 57.691 37.3759 58.0379 30.5376C58.3848 23.6993 56.2977 16.9592 52.1472 11.5135V11.5027Z"
        fill="#1A3B70"
      />
    </svg>
  )
}
