import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import typescript from '@rollup/plugin-typescript';
import copy from 'rollup-plugin-copy';
import dts from 'rollup-plugin-dts';

const production = !process.env.ROLLUP_WATCH;

export default [
  // Main bundles (UMD and ESM)
  {
    input: 'src/index.ts',
    output: [
      {
        file: 'dist/viewer-chat.umd.js',
        format: 'umd',
        name: 'KrionViewerChat',
        sourcemap: !production,
        globals: {}
      },
      {
        file: 'dist/viewer-chat.esm.js',
        format: 'es',
        sourcemap: !production
      }
    ],
    plugins: [
      resolve({
        browser: true
      }),
      commonjs(),
      typescript({
        tsconfig: './tsconfig.json',
        declaration: false,
        declarationDir: undefined
      }),
      copy({
        targets: [
          { src: 'src/styles/*.css', dest: 'dist' }
        ]
      })
    ]
  },
  // Type declarations bundle
  {
    input: 'src/index.ts',
    output: {
      file: 'dist/types/index.d.ts',
      format: 'es'
    },
    plugins: [
      dts({
        tsconfig: './tsconfig.json'
      })
    ],
    external: [/\.css$/]
  }
];
