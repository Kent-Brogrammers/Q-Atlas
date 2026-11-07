<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon from './Icon.svelte';
  let {
    eyebrow,
    title,
    description,
    children
  }: { eyebrow: string; title: string; description: string; children?: Snippet } = $props();
</script>

<section class="feature-banner" aria-label={title}>
  <div class="banner-copy">
    <span class="banner-eyebrow"><span></span>{eyebrow}</span>
    <h2>{title}</h2>
    <p>{description}</p>
    {#if children}<div class="banner-footer">{@render children()}</div>{/if}
  </div>
  <div class="banner-diagram" aria-hidden="true">
    <svg viewBox="0 0 220 190" fill="none">
      <ellipse
        cx="110"
        cy="89"
        rx="79"
        ry="31"
        stroke="#ffffff"
        stroke-opacity=".3"
        transform="rotate(-34 110 89)"
      />
      <ellipse
        cx="110"
        cy="89"
        rx="79"
        ry="31"
        stroke="#ffffff"
        stroke-opacity=".3"
        transform="rotate(34 110 89)"
      />
      <ellipse
        cx="110"
        cy="89"
        rx="79"
        ry="31"
        stroke="#ffffff"
        stroke-opacity=".5"
        transform="rotate(90 110 89)"
      />
      <circle
        cx="110"
        cy="89"
        r="19"
        fill="#fff"
        fill-opacity=".14"
        stroke="#fff"
        stroke-opacity=".55"
      />
      <circle cx="110" cy="89" r="5" fill="white" />
      <circle cx="65" cy="49" r="7" fill="#a6e8ff" /><circle
        cx="164"
        cy="119"
        r="6"
        fill="white"
      /><circle cx="111" cy="15" r="5" fill="#b8ddff" />
      <path d="M39 155h141" stroke="#fff" stroke-opacity=".25" />
      <text
        x="110"
        y="177"
        text-anchor="middle"
        fill="#d9efff"
        font-size="8"
        font-family="IBM Plex Mono, monospace"
        letter-spacing="1">A DIFFERENT PERSPECTIVE</text
      >
    </svg>
    <span class="diagram-corner"><Icon name="northeast" size={16} /></span>
  </div>
</section>

<style>
  .feature-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 18px;
    position: relative;
    min-height: 213px;
    padding: 27px 28px;
    color: white;
    border-radius: 19px;
    background: #0f62fe;
    overflow: hidden;
  }
  .banner-copy {
    position: relative;
    z-index: 1;
    flex: 1;
  }
  .banner-eyebrow {
    display: flex;
    align-items: center;
    gap: 7px;
    color: #f0f7ff;
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.065em;
    text-transform: uppercase;
  }
  .banner-eyebrow > span {
    height: 5px;
    width: 5px;
    background: #a9e2ff;
    border-radius: 50%;
  }
  h2 {
    max-width: 420px;
    margin: 14px 0 10px;
    font-size: 26px;
    font-weight: 500;
    line-height: 1.22;
    letter-spacing: -0.035em;
    color: white;
  }
  p {
    max-width: 410px;
    color: #f0f7ff;
    font-size: 12px;
    line-height: 1.7;
    margin: 0;
  }
  .banner-footer {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    align-items: center;
    margin-top: 23px;
  }
  .banner-footer :global(a) {
    display: inline-flex;
    align-items: center;
    gap: 17px;
    padding: 9px 13px;
    border-radius: 9px;
    background: white;
    color: #1765bf;
    font-size: 10px;
    font-weight: 500;
  }
  .banner-footer :global(a:hover) {
    background: #edf7ff;
  }
  .banner-footer :global(.banner-tag) {
    padding: 4px 9px;
    border: 1px solid #ffffff40;
    border-radius: 30px;
    color: #e3f3ff;
    font-size: 9px;
  }
  .banner-diagram {
    width: 177px;
    align-self: stretch;
    display: flex;
    align-items: center;
    flex-shrink: 0;
    position: relative;
  }
  .banner-diagram svg {
    width: 100%;
  }
  .diagram-corner {
    position: absolute;
    right: -5px;
    top: -5px;
    width: 25px;
    height: 25px;
    border: 1px solid #ffffff35;
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: #d9efff;
  }
  @media (max-width: 1200px) {
    .banner-diagram {
      width: 135px;
    }
    h2 {
      font-size: 24px;
    }
  }
  @media (max-width: 480px) {
    .feature-banner {
      padding: 24px 22px;
      gap: 0;
    }
    .banner-diagram {
      display: none;
    }
    h2 {
      font-size: 25px;
    }
    p {
      font-size: 11px;
    }
  }
</style>
